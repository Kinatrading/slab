from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional
from urllib.parse import quote

import requests
from PyQt6 import QtCore, QtGui, QtWidgets

BASE_DIR = Path(__file__).resolve().parent
STICKERS_FILE = BASE_DIR / "stickers_clean.json"
SLABS_FILE = BASE_DIR / "stickers_slab_clean.json"
CACHE_FILE = BASE_DIR / "market_cache.json"
SETTINGS_FILE = BASE_DIR / "settings.json"


class ItemPair(NamedTuple):
    index: int
    sticker_name: str
    slab_name: str


@dataclass
class RuntimeSettings:
    proxy: Optional[str]
    cookies: Dict[str, str]
    delay: float


class MarketCache:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        if path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                self._data = {}
        else:
            self._data = {}
        self._dirty = False

    def _ensure_entry(self, market_name: str) -> Dict[str, object]:
        with self._lock:
            entry = self._data.setdefault(market_name, {})
            return entry

    def get_item_nameid(self, market_name: str) -> Optional[str]:
        with self._lock:
            entry = self._data.get(market_name)
            if not entry:
                return None
            return entry.get("item_nameid")  # type: ignore[return-value]

    def set_item_nameid(self, market_name: str, item_nameid: str) -> None:
        entry = self._ensure_entry(market_name)
        entry["item_nameid"] = item_nameid
        self._mark_dirty()

    def set_price(self, market_name: str, price: float) -> None:
        entry = self._ensure_entry(market_name)
        entry["last_price"] = price
        entry["updated_at"] = time.time()
        self._mark_dirty()

    def _mark_dirty(self) -> None:
        with self._lock:
            self._dirty = True

    def flush(self) -> None:
        with self._lock:
            if not self._dirty:
                return
            self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
            self._dirty = False


class MarketClient:
    LISTING_URL = "https://steamcommunity.com/market/listings/730/{name}?l=english"
    HISTOGRAM_URL = (
        "https://steamcommunity.com/market/itemordershistogram?country=UA&language=english&currency=18&item_nameid={item_nameid}"
    )

    def __init__(self, cache: MarketCache, settings: RuntimeSettings) -> None:
        self._cache = cache
        self._settings = settings
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        if settings.cookies:
            self._session.cookies.update(settings.cookies)
        proxy_url = self._format_proxy(settings.proxy) if settings.proxy else None
        if proxy_url:
            self._proxies = {"http": proxy_url, "https": proxy_url}
        else:
            self._proxies = None
        self._lock = threading.Lock()
        self._last_request = 0.0

    @staticmethod
    def _format_proxy(proxy: str) -> Optional[str]:
        proxy = proxy.strip()
        if not proxy:
            return None
        parts = proxy.split(":")
        if len(parts) == 2:
            host, port = parts
            auth = ""
        elif len(parts) == 4:
            host, port, user, password = parts
            auth = f"{user}:{password}@"
        else:
            return None
        return f"http://{auth}{host}:{port}"

    def _throttle(self) -> None:
        delay = max(self._settings.delay, 0.05)
        with self._lock:
            elapsed = time.monotonic() - self._last_request
            remaining = delay - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_request = time.monotonic()

    def _request(self, url: str) -> requests.Response:
        print(
            f"[DEBUG] Виконуємо GET {url} | proxy={'on' if self._proxies else 'off'} | "
            f"delay={self._settings.delay:.2f}s"
        )
        self._throttle()
        response = self._session.get(url, proxies=self._proxies, timeout=30)
        print(f"[DEBUG] Відповідь {response.status_code} ({len(response.content)} байт)")
        response.raise_for_status()
        return response

    def ensure_item_nameid(self, market_name: str) -> str:
        cached = self._cache.get_item_nameid(market_name)
        if cached:
            print(f"[DEBUG] item_nameid для '{market_name}' з кешу: {cached}")
            return cached
        encoded = quote(market_name, safe="")
        url = self.LISTING_URL.format(name=encoded)
        print(f"[DEBUG] Listing URL для '{market_name}': {url}")
        response = self._request(url)
        match = re.search(r"Market_LoadOrderSpread\\((\\d+)\\)", response.text)
        if not match:
            snippet = response.text[:1000]
            print(f"[DEBUG] HTML без item_nameid для '{market_name}': {snippet}")
            raise RuntimeError(f"Не вдалося знайти item_nameid для {market_name}")
        item_nameid = match.group(1)
        self._cache.set_item_nameid(market_name, item_nameid)
        print(f"[DEBUG] item_nameid знайдено для '{market_name}': {item_nameid}")
        return item_nameid

    def fetch_price(self, market_name: str) -> float:
        item_nameid = self.ensure_item_nameid(market_name)
        url = self.HISTOGRAM_URL.format(item_nameid=item_nameid)
        print(f"[DEBUG] Histogram URL для '{market_name}': {url}")
        response = self._request(url)
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            print(f"[DEBUG] Не вдалося розпарсити JSON для '{market_name}': {response.text[:500]}")
            raise RuntimeError(f"Некоректний JSON для {market_name}") from exc
        highest = data.get("highest_buy_order")
        if not highest:
            print(f"[DEBUG] highest_buy_order відсутній у відповіді для '{market_name}': {data}")
            return 0.0
        try:
            price = int(highest) / 100.0
        except ValueError as exc:
            raise RuntimeError(f"Неправильний формат highest_buy_order для {market_name}") from exc
        self._cache.set_price(market_name, price)
        print(f"[DEBUG] Оновлена ціна '{market_name}': ₴{price:.2f}")
        return price


class ScanWorker(QtCore.QObject):
    rowUpdated = QtCore.pyqtSignal(int, float, float)
    progressMessage = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, pairs: List[ItemPair], client: MarketClient) -> None:
        super().__init__()
        self._pairs = pairs
        self._client = client
        self._stop_event = threading.Event()

    @QtCore.pyqtSlot()
    def run(self) -> None:
        for pair in self._pairs:
            if self._stop_event.is_set():
                break
            self.progressMessage.emit(
                f"Сканую пару #{pair.index + 1}: {pair.slab_name} / {pair.sticker_name}"
            )
            print(
                f"[DEBUG] Починаємо пару #{pair.index + 1}: slab='{pair.slab_name}', sticker='{pair.sticker_name}'"
            )
            try:
                sticker_price = self._client.fetch_price(pair.sticker_name)
                slab_price = self._client.fetch_price(pair.slab_name)
            except Exception as exc:  # noqa: BLE001 - bubble up to UI
                print(f"[DEBUG] Помилка при обробці пари #{pair.index + 1}: {exc}")
                self.progressMessage.emit(str(exc))
                continue
            print(
                f"[DEBUG] Пара #{pair.index + 1} готова: slab=₴{slab_price:.2f}, sticker=₴{sticker_price:.2f}"
            )
            self.rowUpdated.emit(pair.index, slab_price, sticker_price)
        self.finished.emit()

    def stop(self) -> None:
        self._stop_event.set()


class NumericSortProxy(QtCore.QSortFilterProxyModel):
    def lessThan(
        self,
        left: QtCore.QModelIndex,
        right: QtCore.QModelIndex,
    ) -> bool:  # noqa: D401
        role = QtCore.Qt.ItemDataRole.UserRole
        left_value = left.data(role)
        right_value = right.data(role)
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            return left_value < right_value
        return super().lessThan(left, right)


class SettingsPanel(QtWidgets.QGroupBox):
    def __init__(self) -> None:
        super().__init__("Налаштування")
        self.proxy_input = QtWidgets.QLineEdit()
        self.proxy_input.setPlaceholderText("Host:Port:Username:Password")
        self.cookies_input = QtWidgets.QPlainTextEdit()
        self.cookies_input.setPlaceholderText("sessionid=...; steamLoginSecure=...")
        self.delay_input = QtWidgets.QDoubleSpinBox()
        self.delay_input.setRange(0.05, 10.0)
        self.delay_input.setValue(0.3)
        self.delay_input.setSuffix(" c")
        self.delay_input.setSingleStep(0.05)

        form = QtWidgets.QFormLayout()
        form.addRow("Проксі", self.proxy_input)
        form.addRow("Кукіс", self.cookies_input)
        form.addRow("Затримка", self.delay_input)
        self.setLayout(form)

    def load(self, settings: Dict[str, object]) -> None:
        proxy_value = settings.get("proxy", "")
        cookies_value = settings.get("cookies", "")
        delay_value = settings.get("delay", 0.3)
        self.proxy_input.setText(str(proxy_value) if proxy_value is not None else "")
        self.cookies_input.setPlainText(str(cookies_value) if cookies_value is not None else "")
        try:
            delay = float(delay_value)
        except (TypeError, ValueError):
            delay = 0.3
        self.delay_input.setValue(delay)

    def to_runtime_settings(self) -> RuntimeSettings:
        proxy_text = self.proxy_input.text().strip()
        cookies_text = self.cookies_input.toPlainText().strip()
        cookies = {}
        if cookies_text:
            for chunk in cookies_text.split(";"):
                if "=" not in chunk:
                    continue
                key, value = chunk.split("=", 1)
                cookies[key.strip()] = value.strip()
        delay = self.delay_input.value()
        return RuntimeSettings(proxy=proxy_text, cookies=cookies, delay=delay)

    def export_dict(self) -> Dict[str, object]:
        return {
            "proxy": self.proxy_input.text().strip(),
            "cookies": self.cookies_input.toPlainText().strip(),
            "delay": self.delay_input.value(),
        }


class MainWindow(QtWidgets.QWidget):
    def __init__(self, pairs: List[ItemPair], cache: MarketCache) -> None:
        super().__init__()
        self._pairs = pairs
        self._cache = cache
        self._worker_thread: Optional[QtCore.QThread] = None
        self._worker: Optional[ScanWorker] = None
        self.setWindowTitle("Steam Sticker Scanner")
        self.resize(1100, 700)
        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        self.table_model = QtGui.QStandardItemModel(len(self._pairs), 5)
        self.table_model.setHorizontalHeaderLabels(
            ["Назва слабу", "Назва стікеру", "Ціна слабу", "Ціна стікеру", "Різниця"]
        )
        for row, pair in enumerate(self._pairs):
            slab_item = QtGui.QStandardItem(pair.slab_name)
            sticker_item = QtGui.QStandardItem(pair.sticker_name)
            for item in (slab_item, sticker_item):
                item.setEditable(False)
            self.table_model.setItem(row, 0, slab_item)
            self.table_model.setItem(row, 1, sticker_item)
            for col in range(2, 5):
                placeholder = QtGui.QStandardItem("—")
                placeholder.setEditable(False)
                placeholder.setData(0.0, QtCore.Qt.ItemDataRole.UserRole)
                self.table_model.setItem(row, col, placeholder)

        self.proxy_model = NumericSortProxy()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self.table_view = QtWidgets.QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setStyleSheet(
            "QTableView { background-color: #0d1117; color: #c9d1d9; gridline-color: #30363d; }"
            "QHeaderView::section { background-color: #161b22; color: #58a6ff; border: none; padding: 6px; }"
        )

        self.settings_panel = SettingsPanel()

        self.status_label = QtWidgets.QLabel("Готово")
        self.status_label.setStyleSheet("color: #58a6ff; font-weight: bold;")

        self.scan_button = QtWidgets.QPushButton("Старт сканування")
        self.scan_button.setCheckable(True)
        self.scan_button.clicked.connect(self._toggle_scan)
        self.scan_button.setStyleSheet(
            "QPushButton { background-color: #238636; color: white; padding: 10px; border-radius: 6px; }"
            "QPushButton:checked { background-color: #a40e26; }"
        )

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.table_view)

        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(self.settings_panel)

        right_column = QtWidgets.QVBoxLayout()
        right_column.addWidget(self.status_label)
        right_column.addWidget(self.scan_button)
        right_column.addStretch()
        controls.addLayout(right_column)

        layout.addLayout(controls)
        self.setLayout(layout)
        self.setStyleSheet("background-color: #05090f; color: #c9d1d9; font-size: 14px;")

    def _load_settings(self) -> None:
        if SETTINGS_FILE.exists():
            try:
                settings_data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                settings_data = {}
        else:
            settings_data = {}
        self.settings_panel.load(settings_data)

    def _save_settings(self) -> None:
        SETTINGS_FILE.write_text(json.dumps(self.settings_panel.export_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _toggle_scan(self) -> None:
        if self._worker_thread:
            self._stop_worker()
            return
        self._save_settings()
        runtime_settings = self.settings_panel.to_runtime_settings()
        client = MarketClient(self._cache, runtime_settings)
        self._worker = ScanWorker(self._pairs, client)
        self._worker_thread = QtCore.QThread(self)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.rowUpdated.connect(self._update_row)
        self._worker.progressMessage.connect(self._update_status)
        self._worker.finished.connect(self._handle_finished)
        self._worker_thread.start()
        self.scan_button.setText("Зупинити сканування")
        self.status_label.setText("Сканування...")

    def _stop_worker(self) -> None:
        if self._worker:
            self._worker.stop()
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
        self._worker = None
        self.scan_button.setChecked(False)
        self.scan_button.setText("Старт сканування")
        self.status_label.setText("Зупинено")
        self._cache.flush()

    @QtCore.pyqtSlot(int, float, float)
    def _update_row(self, index: int, slab_price: float, sticker_price: float) -> None:
        def _format_price(value: float) -> str:
            return f"₴{value:.2f}" if value else "—"

        difference = slab_price - sticker_price
        for column, value in zip(
            (2, 3, 4),
            (_format_price(slab_price), _format_price(sticker_price), f"₴{difference:.2f}"),
        ):
            item = self.table_model.item(index, column)
            if item is None:
                item = QtGui.QStandardItem()
                self.table_model.setItem(index, column, item)
            item.setText(value)
            numeric = difference if column == 4 else (slab_price if column == 2 else sticker_price)
            item.setData(numeric, QtCore.Qt.ItemDataRole.UserRole)
            item.setEditable(False)

    @QtCore.pyqtSlot(str)
    def _update_status(self, message: str) -> None:
        self.status_label.setText(message)

    @QtCore.pyqtSlot()
    def _handle_finished(self) -> None:
        self._cache.flush()
        self.status_label.setText("Готово")
        self.scan_button.setChecked(False)
        self.scan_button.setText("Старт сканування")
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
        self._worker = None

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: D401
        self._stop_worker()
        super().closeEvent(event)


def load_pairs() -> List[ItemPair]:
    stickers = json.loads(STICKERS_FILE.read_text(encoding="utf-8"))
    slabs = json.loads(SLABS_FILE.read_text(encoding="utf-8"))
    pairs: List[ItemPair] = []
    for index, (sticker, slab) in enumerate(zip(stickers, slabs)):
        sticker_name = sticker.get("market_hash_name") or sticker.get("name")
        slab_name = slab.get("market_hash_name") or slab.get("name")
        if not sticker_name or not slab_name:
            continue
        pairs.append(ItemPair(index=index, sticker_name=sticker_name, slab_name=slab_name))
    return pairs


def main() -> None:
    pairs = load_pairs()
    if not pairs:
        raise SystemExit("Немає доступних пар предметів")
    cache = MarketCache(CACHE_FILE)
    app = QtWidgets.QApplication([])
    window = MainWindow(pairs, cache)
    window.show()
    app.exec()
    cache.flush()


if __name__ == "__main__":
    main()
