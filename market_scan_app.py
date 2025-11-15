from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, NamedTuple, Optional, Set, Tuple
from urllib.parse import quote

import requests
from PyQt6 import QtCore, QtGui, QtWidgets


SLAB_PRICE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1
STICKER_PRICE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 2
RARITY_ROLE = QtCore.Qt.ItemDataRole.UserRole + 3
CRATES_ROLE = QtCore.Qt.ItemDataRole.UserRole + 4
DIFFERENCE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 5

BASE_DIR = Path(__file__).resolve().parent
STICKERS_FILE = BASE_DIR / "stickers_clean.json"
SLABS_FILE = BASE_DIR / "stickers_slab_clean.json"
CACHE_FILE = BASE_DIR / "market_cache.json"
SETTINGS_FILE = BASE_DIR / "settings.json"


class ItemPair(NamedTuple):
    index: int
    sticker_name: str
    slab_name: str
    rarity_name: str
    crates: Tuple[str, ...]


@dataclass
class RuntimeSettings:
    proxies: List[str]
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
    LISTING_RENDER_URL = (
        "https://steamcommunity.com/market/listings/730/{name}/render?start=0&count=1&country=UA&language=english&currency=18"
    )
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
        self._proxy_pool: List[str] = []
        for entry in settings.proxies:
            formatted = self._format_proxy(entry)
            if formatted:
                self._proxy_pool.append(formatted)
        self._proxy_index = 0
        self._proxy_rotation_hits = 0
        self._status_callback: Optional[Callable[[str], None]] = None
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

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        self._status_callback = callback

    def _emit_status(self, message: str) -> None:
        if self._status_callback:
            self._status_callback(message)

    def _throttle(self) -> None:
        delay = max(self._settings.delay, 0.05)
        with self._lock:
            elapsed = time.monotonic() - self._last_request
            remaining = delay - elapsed
            if remaining > 0:
                time.sleep(remaining)
            self._last_request = time.monotonic()

    def _current_proxy(self) -> Optional[Dict[str, str]]:
        if not self._proxy_pool:
            return None
        current = self._proxy_pool[self._proxy_index]
        return {"http": current, "https": current}

    def _advance_proxy(self) -> None:
        if not self._proxy_pool:
            return
        self._proxy_index = (self._proxy_index + 1) % len(self._proxy_pool)

    def _handle_rate_limit(self, url: str) -> None:
        proxy_state = (
            f"{self._proxy_index + 1}/{len(self._proxy_pool)}" if self._proxy_pool else "без проксі"
        )
        message = f"429 для {url}. Поточний проксі: {proxy_state}"
        print(f"[DEBUG] {message}")
        self._emit_status(message)
        if self._proxy_pool:
            self._proxy_rotation_hits += 1
            self._advance_proxy()
            if self._proxy_rotation_hits >= len(self._proxy_pool):
                wait_message = "Усі проксі дали 429. Пауза 10 хвилин"
                print(f"[DEBUG] {wait_message}")
                self._emit_status(wait_message)
                time.sleep(600)
                self._proxy_rotation_hits = 0
        else:
            wait_message = "429 без проксі. Пауза 10 хвилин"
            print(f"[DEBUG] {wait_message}")
            self._emit_status(wait_message)
            time.sleep(600)

    def _request(self, url: str) -> requests.Response:
        while True:
            proxy_hint = (
                f"{self._proxy_index + 1}/{len(self._proxy_pool)}" if self._proxy_pool else "off"
            )
            print(
                f"[DEBUG] Виконуємо GET {url} | proxy={proxy_hint} | "
                f"delay={self._settings.delay:.2f}s"
            )
            self._throttle()
            response = self._session.get(url, proxies=self._current_proxy(), timeout=30)
            print(f"[DEBUG] Відповідь {response.status_code} ({len(response.content)} байт)")
            if response.status_code == 429:
                self._handle_rate_limit(url)
                continue
            self._proxy_rotation_hits = 0
            response.raise_for_status()
            return response

    def ensure_item_nameid(self, market_name: str) -> str:
        cached = self._cache.get_item_nameid(market_name)
        if cached:
            print(f"[DEBUG] item_nameid для '{market_name}' з кешу: {cached}")
            return cached
        encoded = quote(market_name, safe="")
        try:
            item_nameid = self._fetch_item_nameid_from_render(encoded, market_name)
        except RuntimeError as exc:
            print(f"[DEBUG] Render JSON без item_nameid для '{market_name}': {exc}")
            item_nameid = self._fetch_item_nameid_from_html(encoded, market_name)
        self._cache.set_item_nameid(market_name, item_nameid)
        print(f"[DEBUG] item_nameid знайдено для '{market_name}': {item_nameid}")
        return item_nameid

    def _fetch_item_nameid_from_render(self, encoded_name: str, market_name: str) -> str:
        url = self.LISTING_RENDER_URL.format(name=encoded_name)
        print(f"[DEBUG] Render URL для '{market_name}': {url}")
        response = self._request(url)
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            print(f"[DEBUG] Render JSON не розпарсили для '{market_name}': {response.text[:500]}")
            raise RuntimeError("Некоректний render JSON") from exc
        item_nameid = data.get("item_nameid")
        if not item_nameid:
            raise RuntimeError("item_nameid відсутній у render відповіді")
        return str(item_nameid)

    def _fetch_item_nameid_from_html(self, encoded_name: str, market_name: str) -> str:
        url = self.LISTING_URL.format(name=encoded_name)
        print(f"[DEBUG] Listing URL для '{market_name}': {url}")
        response = self._request(url)
        match = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", response.text)
        if not match:
            snippet = response.text[:1000]
            print(f"[DEBUG] HTML без item_nameid для '{market_name}': {snippet}")
            raise RuntimeError(f"Не вдалося знайти item_nameid для {market_name}")
        return match.group(1)

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
    priceUpdated = QtCore.pyqtSignal(int, bool, float)
    priceFailed = QtCore.pyqtSignal(int, bool, str)
    progressMessage = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, pairs: List[ItemPair], client: MarketClient) -> None:
        super().__init__()
        self._pairs = pairs
        self._client = client
        self._stop_event = threading.Event()
        self._client.set_status_callback(self.progressMessage.emit)

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
            for is_slab, name in ((False, pair.sticker_name), (True, pair.slab_name)):
                if self._stop_event.is_set():
                    break
                label = "slab" if is_slab else "sticker"
                try:
                    price = self._client.fetch_price(name)
                except Exception as exc:  # noqa: BLE001 - bubble up to UI
                    print(
                        f"[DEBUG] Помилка при обробці пари #{pair.index + 1} ({label}): {exc}"
                    )
                    self.progressMessage.emit(str(exc))
                    self.priceFailed.emit(pair.index, is_slab, str(exc))
                    continue
                self.priceUpdated.emit(pair.index, is_slab, price)
                print(
                    f"[DEBUG] {label} ціна для пари #{pair.index + 1}: ₴{price:.2f}"
                )
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
        if left_value is None and right_value is None:
            return False
        if left_value is None:
            return False
        if right_value is None:
            return True
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            return left_value < right_value
        return super().lessThan(left, right)


class PairFilterProxy(NumericSortProxy):
    def __init__(self) -> None:
        super().__init__()
        self.show_priced_only = False
        self.min_price = 0.03
        self.max_price = 90000.0
        self.allowed_rarities: Set[str] = set()
        self.allowed_crates: Set[str] = set()

    def update_filters(
        self,
        *,
        priced_only: bool,
        min_price: float,
        max_price: float,
        rarities: Set[str],
        crates: Set[str],
    ) -> None:
        self.show_priced_only = priced_only
        self.min_price = min_price
        self.max_price = max_price
        self.allowed_rarities = set(rarities)
        self.allowed_crates = set(crates)
        self.invalidateFilter()

    def filterAcceptsRow(
        self,
        source_row: int,
        source_parent: QtCore.QModelIndex,
    ) -> bool:  # noqa: D401
        model = self.sourceModel()
        if model is None:
            return True
        slab_index = model.index(source_row, 2, source_parent)
        sticker_index = model.index(source_row, 3, source_parent)
        info_index = model.index(source_row, 0, source_parent)
        slab_price = slab_index.data(SLAB_PRICE_ROLE)
        sticker_price = sticker_index.data(STICKER_PRICE_ROLE)
        rarity_name = info_index.data(RARITY_ROLE) or ""
        crates = info_index.data(CRATES_ROLE) or ()
        if isinstance(crates, str):
            crate_values = {crates}
        else:
            crate_values = set(crates)

        if self.allowed_rarities and rarity_name not in self.allowed_rarities:
            return False
        if self.allowed_crates and not (crate_values & self.allowed_crates):
            return False

        has_prices = slab_price is not None and sticker_price is not None
        if self.show_priced_only and not has_prices:
            return False

        if slab_price is None and sticker_price is None:
            return True

        def _within(price: Optional[float]) -> bool:
            return price is not None and self.min_price <= price <= self.max_price

        if not (_within(slab_price) or _within(sticker_price)):
            return False
        return True


class FiltersPanel(QtWidgets.QGroupBox):
    filtersChanged = QtCore.pyqtSignal()

    def __init__(self, rarities: List[str], crates: List[str]) -> None:
        super().__init__("Фільтри")
        self.priced_only = QtWidgets.QCheckBox("Показати лише з наявними цінами")
        self.priced_only.toggled.connect(self.filtersChanged.emit)

        self.min_price_input = QtWidgets.QDoubleSpinBox()
        self.min_price_input.setRange(0.03, 90000.0)
        self.min_price_input.setDecimals(2)
        self.min_price_input.setValue(0.03)
        self.min_price_input.valueChanged.connect(self._handle_min_price_change)

        self.max_price_input = QtWidgets.QDoubleSpinBox()
        self.max_price_input.setRange(0.03, 90000.0)
        self.max_price_input.setDecimals(2)
        self.max_price_input.setValue(90000.0)
        self.max_price_input.valueChanged.connect(self._handle_max_price_change)

        self.rarity_button, self._rarity_actions = self._build_menu_button(
            "Усі рідкості", rarities or ["Невідомо"], self._handle_rarity_menu
        )
        self.crates_button, self._crate_actions = self._build_menu_button(
            "Усі крейти", crates, self._handle_crate_menu
        )

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.priced_only)

        price_row = QtWidgets.QHBoxLayout()
        price_row.addWidget(QtWidgets.QLabel("Мін ціна"))
        price_row.addWidget(self.min_price_input)
        price_row.addWidget(QtWidgets.QLabel("Макс ціна"))
        price_row.addWidget(self.max_price_input)
        layout.addLayout(price_row)

        layout.addWidget(self.rarity_button)
        layout.addWidget(self.crates_button)
        layout.addStretch()
        self.setLayout(layout)

    def _build_menu_button(
        self,
        placeholder: str,
        options: List[str],
        handler: Callable[[], None],
    ) -> Tuple[QtWidgets.QToolButton, List[QtGui.QAction]]:
        menu = QtWidgets.QMenu(self)
        actions: List[QtGui.QAction] = []
        for option in options:
            text = option or "Невідомо"
            action = QtGui.QAction(text, self)
            action.setCheckable(True)
            action.toggled.connect(handler)
            action.toggled.connect(self.filtersChanged.emit)
            menu.addAction(action)
            actions.append(action)
        button = QtWidgets.QToolButton()
        button.setText(placeholder)
        button.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        button.setMenu(menu)
        button.setStyleSheet(
            "QToolButton { background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d; padding: 6px; }"
        )
        button.setEnabled(bool(actions))
        return button, actions

    def _handle_min_price_change(self, value: float) -> None:
        self.max_price_input.setMinimum(value)
        self.filtersChanged.emit()

    def _handle_max_price_change(self, value: float) -> None:
        self.min_price_input.setMaximum(value)
        self.filtersChanged.emit()

    def _handle_rarity_menu(self) -> None:
        self._update_button_label(self.rarity_button, "Усі рідкості", self.selected_rarities())

    def _handle_crate_menu(self) -> None:
        self._update_button_label(self.crates_button, "Усі крейти", self.selected_crates())

    @staticmethod
    def _update_button_label(
        button: QtWidgets.QToolButton, default_text: str, selected: Set[str]
    ) -> None:
        if not selected:
            button.setText(default_text)
        elif len(selected) == 1:
            button.setText(next(iter(selected)))
        else:
            button.setText(f"Обрано: {len(selected)}")

    def selected_rarities(self) -> Set[str]:
        return {action.text() for action in self._rarity_actions if action.isChecked()}

    def selected_crates(self) -> Set[str]:
        return {action.text() for action in self._crate_actions if action.isChecked()}

    def export_filters(self) -> Dict[str, object]:
        return {
            "priced_only": self.priced_only.isChecked(),
            "min_price": float(self.min_price_input.value()),
            "max_price": float(self.max_price_input.value()),
            "rarities": self.selected_rarities(),
            "crates": self.selected_crates(),
        }

    def filter_pairs_for_scan(self, pairs: List[ItemPair]) -> List[ItemPair]:
        rarity_filter = self.selected_rarities()
        crate_filter = self.selected_crates()
        if not rarity_filter and not crate_filter:
            return list(pairs)
        filtered: List[ItemPair] = []
        for pair in pairs:
            if rarity_filter and pair.rarity_name not in rarity_filter:
                continue
            if crate_filter and not (set(pair.crates) & crate_filter):
                continue
            filtered.append(pair)
        return filtered


class SettingsPanel(QtWidgets.QGroupBox):
    def __init__(self) -> None:
        super().__init__("Налаштування")
        self.proxy_input = QtWidgets.QPlainTextEdit()
        self.proxy_input.setPlaceholderText("Один проксі на рядок у форматі Host:Port[:User:Pass]")
        self.proxy_input.setFixedHeight(80)
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
        self.proxy_input.setPlainText(str(proxy_value) if proxy_value is not None else "")
        self.cookies_input.setPlainText(str(cookies_value) if cookies_value is not None else "")
        try:
            delay = float(delay_value)
        except (TypeError, ValueError):
            delay = 0.3
        self.delay_input.setValue(delay)

    def to_runtime_settings(self) -> RuntimeSettings:
        proxy_text = self.proxy_input.toPlainText().strip()
        proxies = [line.strip() for line in proxy_text.splitlines() if line.strip()]
        cookies_text = self.cookies_input.toPlainText().strip()
        cookies = {}
        if cookies_text:
            for chunk in cookies_text.split(";"):
                if "=" not in chunk:
                    continue
                key, value = chunk.split("=", 1)
                cookies[key.strip()] = value.strip()
        delay = self.delay_input.value()
        return RuntimeSettings(proxies=proxies, cookies=cookies, delay=delay)

    def export_dict(self) -> Dict[str, object]:
        return {
            "proxy": self.proxy_input.toPlainText().strip(),
            "cookies": self.cookies_input.toPlainText().strip(),
            "delay": self.delay_input.value(),
        }


class MainWindow(QtWidgets.QWidget):
    def __init__(self, pairs: List[ItemPair], cache: MarketCache, rarities: List[str], crates: List[str]) -> None:
        super().__init__()
        self._pairs = pairs
        self._cache = cache
        self._available_rarities = rarities
        self._available_crates = crates
        self._worker_thread: Optional[QtCore.QThread] = None
        self._worker: Optional[ScanWorker] = None
        self._row_prices = {
            pair.index: {"slab": None, "sticker": None} for pair in self._pairs
        }
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
            slab_item.setData(pair.rarity_name, RARITY_ROLE)
            slab_item.setData(pair.crates, CRATES_ROLE)
            self.table_model.setItem(row, 0, slab_item)
            self.table_model.setItem(row, 1, sticker_item)
            for col in range(2, 5):
                placeholder = QtGui.QStandardItem("—")
                placeholder.setEditable(False)
                placeholder.setData(None, QtCore.Qt.ItemDataRole.UserRole)
                role = (
                    SLAB_PRICE_ROLE
                    if col == 2
                    else STICKER_PRICE_ROLE
                    if col == 3
                    else DIFFERENCE_ROLE
                )
                placeholder.setData(None, role)
                self.table_model.setItem(row, col, placeholder)

        self.proxy_model = PairFilterProxy()
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

        self.filters_panel = FiltersPanel(self._available_rarities, self._available_crates)
        self.filters_panel.filtersChanged.connect(self._apply_filters)

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
        controls.addWidget(self.filters_panel)
        controls.addWidget(self.settings_panel)

        right_column = QtWidgets.QVBoxLayout()
        right_column.addWidget(self.status_label)
        right_column.addWidget(self.scan_button)
        right_column.addStretch()
        controls.addLayout(right_column)

        layout.addLayout(controls)
        self.setLayout(layout)
        self.setStyleSheet("background-color: #05090f; color: #c9d1d9; font-size: 14px;")
        self._apply_filters()

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

    def _apply_filters(self) -> None:
        if not hasattr(self, "proxy_model"):
            return
        filters = self.filters_panel.export_filters()
        self.proxy_model.update_filters(
            priced_only=bool(filters["priced_only"]),
            min_price=float(filters["min_price"]),
            max_price=float(filters["max_price"]),
            rarities=set(filters["rarities"]),
            crates=set(filters["crates"]),
        )

    def _toggle_scan(self) -> None:
        if self._worker_thread:
            self._stop_worker()
            return
        self._save_settings()
        scan_pairs = self.filters_panel.filter_pairs_for_scan(self._pairs)
        if not scan_pairs:
            self.status_label.setText("Немає предметів, що відповідають фільтрам")
            self.scan_button.setChecked(False)
            return
        runtime_settings = self.settings_panel.to_runtime_settings()
        client = MarketClient(self._cache, runtime_settings)
        self._worker = ScanWorker(scan_pairs, client)
        self._worker_thread = QtCore.QThread(self)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.priceUpdated.connect(self._handle_price_update)
        self._worker.priceFailed.connect(self._handle_price_failure)
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

    @QtCore.pyqtSlot(int, bool, float)
    def _handle_price_update(self, index: int, is_slab: bool, price: float) -> None:
        column = 2 if is_slab else 3
        role = SLAB_PRICE_ROLE if is_slab else STICKER_PRICE_ROLE
        item = self.table_model.item(index, column)
        if item is None:
            item = QtGui.QStandardItem()
            self.table_model.setItem(index, column, item)
        item.setText(f"₴{price:.2f}")
        item.setData(price, QtCore.Qt.ItemDataRole.UserRole)
        item.setData(price, role)
        item.setEditable(False)
        key = "slab" if is_slab else "sticker"
        self._row_prices.setdefault(index, {})[key] = price
        self._update_difference_cell(index)
        self.proxy_model.invalidateFilter()

    @QtCore.pyqtSlot(int, bool, str)
    def _handle_price_failure(self, index: int, is_slab: bool, message: str) -> None:
        column = 2 if is_slab else 3
        role = SLAB_PRICE_ROLE if is_slab else STICKER_PRICE_ROLE
        item = self.table_model.item(index, column)
        if item is None:
            item = QtGui.QStandardItem()
            self.table_model.setItem(index, column, item)
        item.setText(message)
        item.setData(None, QtCore.Qt.ItemDataRole.UserRole)
        item.setData(None, role)
        item.setEditable(False)
        key = "slab" if is_slab else "sticker"
        self._row_prices.setdefault(index, {})[key] = None
        self._update_difference_cell(index)
        self.proxy_model.invalidateFilter()

    def _update_difference_cell(self, index: int) -> None:
        item = self.table_model.item(index, 4)
        if item is None:
            item = QtGui.QStandardItem("—")
            self.table_model.setItem(index, 4, item)
        slab_price = self._row_prices.setdefault(index, {}).get("slab")
        sticker_price = self._row_prices.setdefault(index, {}).get("sticker")
        if slab_price is not None and sticker_price is not None:
            diff = slab_price - sticker_price
            item.setText(f"₴{diff:.2f}")
            item.setData(diff, QtCore.Qt.ItemDataRole.UserRole)
            item.setData(diff, DIFFERENCE_ROLE)
        else:
            item.setText("Очікуємо дані")
            item.setData(None, QtCore.Qt.ItemDataRole.UserRole)
            item.setData(None, DIFFERENCE_ROLE)
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


def load_pairs() -> Tuple[List[ItemPair], List[str], List[str]]:
    stickers = json.loads(STICKERS_FILE.read_text(encoding="utf-8"))
    slabs = json.loads(SLABS_FILE.read_text(encoding="utf-8"))
    pairs: List[ItemPair] = []
    rarities: Set[str] = set()
    crates: Set[str] = set()
    for sticker, slab in zip(stickers, slabs):
        sticker_name = sticker.get("market_hash_name") or sticker.get("name")
        slab_name = slab.get("market_hash_name") or slab.get("name")
        if not sticker_name or not slab_name:
            continue
        rarity_name = (sticker.get("rarity") or {}).get("name") or "Невідомо"
        crate_names = tuple(
            crate.get("name")
            for crate in sticker.get("crates", [])
            if isinstance(crate, dict) and crate.get("name")
        )
        rarities.add(rarity_name)
        crates.update(crate_names)
        pairs.append(
            ItemPair(
                index=len(pairs),
                sticker_name=sticker_name,
                slab_name=slab_name,
                rarity_name=rarity_name,
                crates=crate_names,
            )
        )
    return pairs, sorted(rarities), sorted(crates)


def main() -> None:
    pairs, rarities, crates = load_pairs()
    if not pairs:
        raise SystemExit("Немає доступних пар предметів")
    cache = MarketCache(CACHE_FILE)
    app = QtWidgets.QApplication([])
    window = MainWindow(pairs, cache, rarities, crates)
    window.show()
    app.exec()
    cache.flush()


if __name__ == "__main__":
    main()
