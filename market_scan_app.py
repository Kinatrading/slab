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
ITEM_NAMEID_ROLE = QtCore.Qt.ItemDataRole.UserRole + 6
SELL_PRICE_ROLE = QtCore.Qt.ItemDataRole.UserRole + 7

BASE_DIR = Path(__file__).resolve().parent
STICKERS_FILE = BASE_DIR / "stickers_clean.json"
SLABS_FILE = BASE_DIR / "stickers_slab_clean.json"
CACHE_FILE = BASE_DIR / "market_cache.json"
SETTINGS_FILE = BASE_DIR / "settings.json"
ITEM_NAMEIDS_FILE = BASE_DIR / "item_nameids.json"


class Translator:
    DEFAULT_LANGUAGE = "uk"

    _TRANSLATIONS: Dict[str, Dict[str, str]] = {
        "uk": {
            "filters_title": "Фільтри",
            "filters_priced_only": "Показати лише з наявними цінами",
            "filters_all_rarities": "Усі рідкості",
            "filters_all_crates": "Усі крейти",
            "filters_min_price": "Мін ціна",
            "filters_max_price": "Макс ціна",
            "filters_unknown": "Невідомо",
            "filters_selected": "Обрано: {count}",
            "settings_title": "Налаштування",
            "settings_proxy": "Проксі",
            "settings_cookies": "Кукіс",
            "settings_delay": "Затримка",
            "settings_language": "Мова",
            "settings_proxy_placeholder": "Один проксі на рядок у форматі Host:Port[:User:Pass]",
            "settings_cookies_placeholder": "sessionid=...; steamLoginSecure=...",
            "language_uk": "Українська",
            "language_en": "English",
            "table_slab": "Назва слабу",
            "table_sticker": "Назва стікеру",
            "table_slab_price": "Ціна слабу (купівля/продаж)",
            "table_sticker_price": "Ціна стікеру (купівля/продаж)",
            "table_item_nameid": "item_nameid",
            "table_difference": "Різниця",
            "fullscreen_open": "На весь екран",
            "fullscreen_close": "Згорнути",
            "export_button": "Експортувати",
            "message_export_title": "Експорт таблиці",
            "message_export_success": "Експортовано {count} рядків",
            "message_export_empty": "Немає рядків для експорту",
            "message_export_error": "Не вдалося зберегти таблицю: {error}",
            "manual_placeholder": "Введіть назву стікеру або слабу...",
            "manual_save": "Зберегти базу",
            "manual_import": "Імпортувати базу",
            "manual_search": "Пошук пар",
            "tab_all_pairs": "Усі пари",
            "tab_selected_pairs": "Обрані пари",
            "tab_inventory_pairs": "Інвентар",
            "status_ready": "Готово",
            "status_scanning": "Сканування...",
            "status_stopped": "Зупинено",
            "status_add_pairs": "Додайте пари у вкладці 'Обрані пари'",
            "status_no_results": "Немає предметів, що відповідають фільтрам",
            "scan_start": "Старт сканування",
            "scan_stop": "Зупинити сканування",
            "scan_pair": "Сканую пару #{index}: {slab} / {sticker}",
            "manual_label_slab": "— слаб",
            "manual_label_sticker": "— стікер",
            "message_empty_list": "Порожній список",
            "message_no_pairs_to_save": "Немає пар для збереження",
            "message_base_name": "Назва бази",
            "message_enter_base_name": "Введіть назву бази",
            "message_error": "Помилка",
            "message_invalid_base_name": "Некоректна назва бази",
            "message_save_base": "Зберегти базу",
            "message_done": "Готово",
            "message_base_saved": "Базу збережено",
            "message_import_base": "Імпортувати базу",
            "message_file_read_error": "Не вдалося прочитати файл: {exc}",
            "message_invalid_file": "Некоректний формат файлу",
            "message_result": "Результат",
            "message_import_result": "Імпортовано {added} пар",
            "message_import_skipped": ", пропущено {missing}",
            "waiting_data": "Очікуємо дані",
            "no_pairs_available": "Немає доступних пар предметів",
            "status_rate_limit": "429 для {url}. Поточний проксі: {proxy_state}",
            "status_all_proxies_wait": "Усі проксі дали 429. Пауза 10 хвилин",
            "status_no_proxy_wait": "429 без проксі. Пауза 10 хвилин",
            "status_proxy_off": "без проксі",
            "render_json_invalid": "Некоректний render JSON",
            "render_missing_item": "item_nameid відсутній у render відповіді",
            "missing_item_nameid": "Не вдалося знайти item_nameid для {name}",
            "invalid_json": "Некоректний JSON для {name}",
            "invalid_highest": "Неправильний формат highest_buy_order для {name}",
            "inventory_link_label": "Посилання на інвентар",
            "inventory_fetch": "Отримати стікери",
            "inventory_placeholder": "https://steamcommunity.com/id/.../inventory",
            "inventory_status_idle": "Очікуємо посилання",
            "inventory_status_loading": "Завантаження інвентарю...",
            "inventory_status_error": "Помилка: {details}",
            "inventory_status_no_stickers": "Стікери не знайдені",
            "inventory_status_no_pairs": "Немає пар для знайдених стікерів",
            "inventory_status_found": "Знайдено {count} стікерів",
            "inventory_invalid_link": "Некоректне посилання",
            "price_buy": "Купівля",
            "price_sell": "Продаж",
        },
        "en": {
            "filters_title": "Filters",
            "filters_priced_only": "Show only items with prices",
            "filters_all_rarities": "All rarities",
            "filters_all_crates": "All crates",
            "filters_min_price": "Min price",
            "filters_max_price": "Max price",
            "filters_unknown": "Unknown",
            "filters_selected": "Selected: {count}",
            "settings_title": "Settings",
            "settings_proxy": "Proxies",
            "settings_cookies": "Cookies",
            "settings_delay": "Delay",
            "settings_language": "Language",
            "settings_proxy_placeholder": "One proxy per line, Host:Port[:User:Pass]",
            "settings_cookies_placeholder": "sessionid=...; steamLoginSecure=...",
            "language_uk": "Ukrainian",
            "language_en": "English",
            "table_slab": "Slab name",
            "table_sticker": "Sticker name",
            "table_slab_price": "Slab price (buy/sell)",
            "table_sticker_price": "Sticker price (buy/sell)",
            "table_item_nameid": "item_nameid",
            "table_difference": "Difference",
            "fullscreen_open": "Full screen",
            "fullscreen_close": "Restore",
            "export_button": "Export",
            "message_export_title": "Export table",
            "message_export_success": "Exported {count} rows",
            "message_export_empty": "No rows to export",
            "message_export_error": "Failed to save the table: {error}",
            "manual_placeholder": "Enter sticker or slab name...",
            "manual_save": "Save base",
            "manual_import": "Import base",
            "manual_search": "Pair search",
            "tab_all_pairs": "All pairs",
            "tab_selected_pairs": "Selected pairs",
            "tab_inventory_pairs": "Inventory",
            "status_ready": "Ready",
            "status_scanning": "Scanning...",
            "status_stopped": "Stopped",
            "status_add_pairs": "Add pairs on the 'Selected pairs' tab",
            "status_no_results": "No items match the filters",
            "scan_start": "Start scan",
            "scan_stop": "Stop scan",
            "scan_pair": "Scanning pair #{index}: {slab} / {sticker}",
            "manual_label_slab": "— slab",
            "manual_label_sticker": "— sticker",
            "message_empty_list": "Empty list",
            "message_no_pairs_to_save": "No pairs to save",
            "message_base_name": "Base name",
            "message_enter_base_name": "Enter base name",
            "message_error": "Error",
            "message_invalid_base_name": "Invalid base name",
            "message_save_base": "Save base",
            "message_done": "Done",
            "message_base_saved": "Base saved",
            "message_import_base": "Import base",
            "message_file_read_error": "Failed to read file: {exc}",
            "message_invalid_file": "Invalid file format",
            "message_result": "Result",
            "message_import_result": "Imported {added} pairs",
            "message_import_skipped": ", skipped {missing}",
            "waiting_data": "Waiting for data",
            "no_pairs_available": "No item pairs available",
            "status_rate_limit": "429 for {url}. Current proxy: {proxy_state}",
            "status_all_proxies_wait": "All proxies returned 429. Pausing for 10 minutes",
            "status_no_proxy_wait": "429 without proxies. Pausing for 10 minutes",
            "status_proxy_off": "no proxy",
            "render_json_invalid": "Invalid render JSON",
            "render_missing_item": "item_nameid missing in render response",
            "missing_item_nameid": "Could not find item_nameid for {name}",
            "invalid_json": "Invalid JSON for {name}",
            "invalid_highest": "Invalid highest_buy_order format for {name}",
            "inventory_link_label": "Inventory link",
            "inventory_fetch": "Fetch stickers",
            "inventory_placeholder": "https://steamcommunity.com/id/.../inventory",
            "inventory_status_idle": "Waiting for link",
            "inventory_status_loading": "Loading inventory...",
            "inventory_status_error": "Error: {details}",
            "inventory_status_no_stickers": "No stickers found",
            "inventory_status_no_pairs": "No pairs for found stickers",
            "inventory_status_found": "Found {count} stickers",
            "inventory_invalid_link": "Invalid link",
            "price_buy": "Buy",
            "price_sell": "Sell",
        },
    }

    def __init__(self, language: Optional[str] = None) -> None:
        self.language = language or self.DEFAULT_LANGUAGE
        if self.language not in self._TRANSLATIONS:
            self.language = self.DEFAULT_LANGUAGE

    def set_language(self, language: str) -> None:
        self.language = language if language in self._TRANSLATIONS else self.DEFAULT_LANGUAGE

    def t(self, key: str, **kwargs: object) -> str:
        template = self._TRANSLATIONS.get(self.language, {}).get(key)
        if template is None:
            template = self._TRANSLATIONS[self.DEFAULT_LANGUAGE].get(key, key)
        return template.format(**kwargs)

    def languages(self) -> List[str]:
        return list(self._TRANSLATIONS.keys())

    def language_label(self, code: str) -> str:
        return self._TRANSLATIONS.get(self.language, {}).get(f"language_{code}", code)


def load_settings_file() -> Dict[str, object]:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


class ItemPair(NamedTuple):
    index: int
    sticker_name: str
    slab_name: str
    rarity_name: str
    crates: Tuple[str, ...]


@dataclass
class PriceInfo:
    buy: Optional[float]
    sell: Optional[float]


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

    def set_price(self, market_name: str, price: PriceInfo) -> None:
        entry = self._ensure_entry(market_name)
        entry["last_price"] = price.buy
        entry["last_sell_price"] = price.sell
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


class ItemNameIdStore:
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

    def get(self, market_name: str) -> Optional[str]:
        with self._lock:
            value = self._data.get(market_name)
            if isinstance(value, str):
                return value
            return None

    def set(self, market_name: str, item_nameid: str) -> None:
        with self._lock:
            self._data[market_name] = item_nameid
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

    def __init__(
        self, cache: MarketCache, item_store: ItemNameIdStore, settings: RuntimeSettings, translator: Translator
    ) -> None:
        self._cache = cache
        self._item_store = item_store
        self._settings = settings
        self._translator = translator
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
        self._stop_event: Optional[threading.Event] = None
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

    def set_stop_event(self, stop_event: Optional[threading.Event]) -> None:
        self._stop_event = stop_event

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
            f"{self._proxy_index + 1}/{len(self._proxy_pool)}"
            if self._proxy_pool
            else self._translator.t("status_proxy_off")
        )
        message = self._translator.t("status_rate_limit", url=url, proxy_state=proxy_state)
        print(f"[DEBUG] {message}")
        self._emit_status(message)
        if self._proxy_pool:
            self._proxy_rotation_hits += 1
            self._advance_proxy()
            if self._proxy_rotation_hits >= len(self._proxy_pool):
                wait_message = self._translator.t("status_all_proxies_wait")
                print(f"[DEBUG] {wait_message}")
                self._emit_status(wait_message)
                self._sleep_with_stop_check(600)
                self._proxy_rotation_hits = 0
        else:
            wait_message = self._translator.t("status_no_proxy_wait")
            print(f"[DEBUG] {wait_message}")
            self._emit_status(wait_message)
            self._sleep_with_stop_check(600)

    def _sleep_with_stop_check(self, duration: float) -> None:
        if duration <= 0:
            return
        remaining = duration
        interval = 0.5
        while remaining > 0:
            if self._stop_event and self._stop_event.is_set():
                raise RuntimeError(self._translator.t("status_stopped"))
            sleep_time = min(interval, remaining)
            time.sleep(sleep_time)
            remaining -= sleep_time

    def _request(self, url: str) -> requests.Response:
        while True:
            if self._stop_event and self._stop_event.is_set():
                raise RuntimeError(self._translator.t("status_stopped"))
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
        cached = self._item_store.get(market_name)
        if cached:
            print(f"[DEBUG] item_nameid для '{market_name}' з item store: {cached}")
            return cached
        cached = self._cache.get_item_nameid(market_name)
        if cached:
            print(f"[DEBUG] item_nameid для '{market_name}' з кешу: {cached}")
            self._item_store.set(market_name, cached)
            return cached
        encoded = quote(market_name, safe="")
        try:
            item_nameid = self._fetch_item_nameid_from_render(encoded, market_name)
        except RuntimeError as exc:
            print(f"[DEBUG] Render JSON без item_nameid для '{market_name}': {exc}")
            item_nameid = self._fetch_item_nameid_from_html(encoded, market_name)
        self._cache.set_item_nameid(market_name, item_nameid)
        self._item_store.set(market_name, item_nameid)
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
            raise RuntimeError(self._translator.t("render_json_invalid")) from exc
        item_nameid = data.get("item_nameid")
        if not item_nameid:
            raise RuntimeError(self._translator.t("render_missing_item"))
        return str(item_nameid)

    def _fetch_item_nameid_from_html(self, encoded_name: str, market_name: str) -> str:
        url = self.LISTING_URL.format(name=encoded_name)
        print(f"[DEBUG] Listing URL для '{market_name}': {url}")
        response = self._request(url)
        match = re.search(r"Market_LoadOrderSpread\(\s*(\d+)\s*\)", response.text)
        if not match:
            snippet = response.text[:1000]
            print(f"[DEBUG] HTML без item_nameid для '{market_name}': {snippet}")
            raise RuntimeError(self._translator.t("missing_item_nameid", name=market_name))
        return match.group(1)

    def fetch_price(self, market_name: str, item_nameid: Optional[str] = None) -> PriceInfo:
        item_nameid = item_nameid or self.ensure_item_nameid(market_name)
        url = self.HISTOGRAM_URL.format(item_nameid=item_nameid)
        print(f"[DEBUG] Histogram URL для '{market_name}': {url}")
        response = self._request(url)
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            print(f"[DEBUG] Не вдалося розпарсити JSON для '{market_name}': {response.text[:500]}")
            raise RuntimeError(self._translator.t("invalid_json", name=market_name)) from exc
        highest = data.get("highest_buy_order")
        lowest = data.get("lowest_sell_order")
        buy_price: Optional[float]
        sell_price: Optional[float]
        if highest:
            try:
                buy_price = int(highest) / 100.0
            except ValueError as exc:
                raise RuntimeError(self._translator.t("invalid_highest", name=market_name)) from exc
        else:
            print(f"[DEBUG] highest_buy_order відсутній у відповіді для '{market_name}': {data}")
            buy_price = None
        if lowest:
            try:
                sell_price = int(lowest) / 100.0
            except ValueError:
                sell_price = None
        else:
            sell_price = None
        price_info = PriceInfo(buy=buy_price, sell=sell_price)
        self._cache.set_price(market_name, price_info)
        debug_buy = f"₴{buy_price:.2f}" if buy_price is not None else "—"
        debug_sell = f"₴{sell_price:.2f}" if sell_price is not None else "—"
        print(
            f"[DEBUG] Оновлені ціни '{market_name}': buy={debug_buy}, sell={debug_sell}"
        )
        return price_info


class ScanWorker(QtCore.QObject):
    priceUpdated = QtCore.pyqtSignal(int, bool, object)
    priceFailed = QtCore.pyqtSignal(int, bool, str)
    itemIdResolved = QtCore.pyqtSignal(int, bool, str)
    progressMessage = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(self, pairs: List[ItemPair], client: MarketClient, translator: Translator) -> None:
        super().__init__()
        self._pairs = pairs
        self._client = client
        self._translator = translator
        self._stop_event = threading.Event()
        self._client.set_status_callback(self.progressMessage.emit)
        self._client.set_stop_event(self._stop_event)

    @QtCore.pyqtSlot()
    def run(self) -> None:
        for pair in self._pairs:
            if self._stop_event.is_set():
                break
            self.progressMessage.emit(
                self._translator.t(
                    "scan_pair", index=pair.index + 1, slab=pair.slab_name, sticker=pair.sticker_name
                )
            )
            print(
                f"[DEBUG] Починаємо пару #{pair.index + 1}: slab='{pair.slab_name}', sticker='{pair.sticker_name}'"
            )
            for is_slab, name in ((False, pair.sticker_name), (True, pair.slab_name)):
                if self._stop_event.is_set():
                    break
                label = "slab" if is_slab else "sticker"
                try:
                    item_nameid = self._client.ensure_item_nameid(name)
                    self.itemIdResolved.emit(pair.index, is_slab, item_nameid)
                    price = self._client.fetch_price(name, item_nameid=item_nameid)
                except Exception as exc:  # noqa: BLE001 - bubble up to UI
                    print(
                        f"[DEBUG] Помилка при обробці пари #{pair.index + 1} ({label}): {exc}"
                    )
                    self.progressMessage.emit(str(exc))
                    self.priceFailed.emit(pair.index, is_slab, str(exc))
                    continue
                self.priceUpdated.emit(pair.index, is_slab, price)
                buy_text = f"₴{price.buy:.2f}" if price.buy is not None else "—"
                sell_text = f"₴{price.sell:.2f}" if price.sell is not None else "—"
                print(
                    f"[DEBUG] {label} ціна для пари #{pair.index + 1}: buy={buy_text}, sell={sell_text}"
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

    def __init__(self, rarities: List[str], crates: List[str], translator: Translator) -> None:
        self._translator = translator
        self._available_rarities = rarities
        self._available_crates = crates
        super().__init__(self._translator.t("filters_title"))
        self.priced_only = QtWidgets.QCheckBox(self._translator.t("filters_priced_only"))
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
            self._translator.t("filters_all_rarities"),
            rarities or [self._translator.t("filters_unknown")],
            self._handle_rarity_menu,
        )
        self.crates_button, self._crate_actions = self._build_menu_button(
            self._translator.t("filters_all_crates"), crates, self._handle_crate_menu
        )

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.priced_only)

        price_row = QtWidgets.QHBoxLayout()
        price_row.addWidget(QtWidgets.QLabel(self._translator.t("filters_min_price")))
        price_row.addWidget(self.min_price_input)
        price_row.addWidget(QtWidgets.QLabel(self._translator.t("filters_max_price")))
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
            text = option or self._translator.t("filters_unknown")
            action = QtGui.QAction(text, self)
            action.setData(option)
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
        self._update_button_label(
            self.rarity_button, self._translator.t("filters_all_rarities"), self.selected_rarities()
        )

    def _handle_crate_menu(self) -> None:
        self._update_button_label(
            self.crates_button, self._translator.t("filters_all_crates"), self.selected_crates()
        )

    @staticmethod
    def _update_button_label(
        button: QtWidgets.QToolButton, default_text: str, selected: Set[str]
    ) -> None:
        if not selected:
            button.setText(default_text)
        elif len(selected) == 1:
            button.setText(next(iter(selected)))
        else:
            button.setText(self._translator.t("filters_selected", count=len(selected)))

    def selected_rarities(self) -> Set[str]:
        return {action.data() for action in self._rarity_actions if action.isChecked()}

    def selected_crates(self) -> Set[str]:
        return {action.data() for action in self._crate_actions if action.isChecked()}

    def export_filters(self) -> Dict[str, object]:
        return {
            "priced_only": self.priced_only.isChecked(),
            "min_price": float(self.min_price_input.value()),
            "max_price": float(self.max_price_input.value()),
            "rarities": self.selected_rarities(),
            "crates": self.selected_crates(),
        }

    def retranslate(self) -> None:
        self.setTitle(self._translator.t("filters_title"))
        self.priced_only.setText(self._translator.t("filters_priced_only"))
        self.rarity_button.setText(self._translator.t("filters_all_rarities"))
        self.crates_button.setText(self._translator.t("filters_all_crates"))
        self._relabel_actions(self._rarity_actions, self._available_rarities, is_rarity=True)
        self._relabel_actions(self._crate_actions, self._available_crates, is_rarity=False)
        self._update_button_label(self.rarity_button, self._translator.t("filters_all_rarities"), self.selected_rarities())
        self._update_button_label(self.crates_button, self._translator.t("filters_all_crates"), self.selected_crates())

    def _relabel_actions(
        self, actions: List[QtGui.QAction], options: List[str], *, is_rarity: bool
    ) -> None:
        unknown_label = self._translator.t("filters_unknown")
        unknown_values = {values.get("filters_unknown") for values in Translator._TRANSLATIONS.values()}  # type: ignore[attr-defined]
        for action, option in zip(actions, options):
            is_unknown = is_rarity and (not option or option in unknown_values)
            label = unknown_label if is_unknown else option or unknown_label
            action.setText(label)

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
    languageChanged = QtCore.pyqtSignal(str)

    def __init__(self, translator: Translator) -> None:
        self._translator = translator
        super().__init__(self._translator.t("settings_title"))
        self.proxy_input = QtWidgets.QPlainTextEdit()
        self.proxy_input.setPlaceholderText(self._translator.t("settings_proxy_placeholder"))
        self.proxy_input.setFixedHeight(80)
        self.cookies_input = QtWidgets.QPlainTextEdit()
        self.cookies_input.setPlaceholderText(self._translator.t("settings_cookies_placeholder"))
        self.delay_input = QtWidgets.QDoubleSpinBox()
        self.delay_input.setRange(0.05, 10.0)
        self.delay_input.setValue(0.3)
        self.delay_input.setSuffix(" c")
        self.delay_input.setSingleStep(0.05)
        self.language_input = QtWidgets.QComboBox()
        for code in self._translator.languages():
            self.language_input.addItem(self._translator.language_label(code), code)
        self.language_input.currentIndexChanged.connect(self._emit_language_change)

        form = QtWidgets.QFormLayout()
        form.addRow(self._translator.t("settings_proxy"), self.proxy_input)
        form.addRow(self._translator.t("settings_cookies"), self.cookies_input)
        form.addRow(self._translator.t("settings_delay"), self.delay_input)
        form.addRow(self._translator.t("settings_language"), self.language_input)
        self.setLayout(form)

    def load(self, settings: Dict[str, object]) -> None:
        proxy_value = settings.get("proxy", "")
        cookies_value = settings.get("cookies", "")
        delay_value = settings.get("delay", 0.3)
        language = settings.get("language")
        if isinstance(language, str):
            self._translator.set_language(language)
        self.proxy_input.setPlainText(str(proxy_value) if proxy_value is not None else "")
        self.cookies_input.setPlainText(str(cookies_value) if cookies_value is not None else "")
        try:
            delay = float(delay_value)
        except (TypeError, ValueError):
            delay = 0.3
        self.delay_input.setValue(delay)
        self._select_language(self._translator.language)

    def _select_language(self, code: str) -> None:
        for index in range(self.language_input.count()):
            if self.language_input.itemData(index) == code:
                self.language_input.setCurrentIndex(index)
                break

    def _emit_language_change(self) -> None:
        code = self.language_input.currentData()
        if isinstance(code, str):
            self.languageChanged.emit(code)

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
            "language": self.language_input.currentData(),
        }

    def retranslate(self) -> None:
        self.setTitle(self._translator.t("settings_title"))
        self.proxy_input.setPlaceholderText(self._translator.t("settings_proxy_placeholder"))
        self.cookies_input.setPlaceholderText(self._translator.t("settings_cookies_placeholder"))
        for index in range(self.language_input.count()):
            code = self.language_input.itemData(index)
            if isinstance(code, str):
                self.language_input.setItemText(index, self._translator.language_label(code))
        form = self.layout()
        if isinstance(form, QtWidgets.QFormLayout):
            form.labelForField(self.proxy_input).setText(self._translator.t("settings_proxy"))
            form.labelForField(self.cookies_input).setText(self._translator.t("settings_cookies"))
            form.labelForField(self.delay_input).setText(self._translator.t("settings_delay"))
            form.labelForField(self.language_input).setText(self._translator.t("settings_language"))


class MainWindow(QtWidgets.QWidget):
    def __init__(
        self,
        pairs: List[ItemPair],
        cache: MarketCache,
        item_store: ItemNameIdStore,
        rarities: List[str],
        crates: List[str],
        translator: Translator,
        settings: Optional[Dict[str, object]] = None,
    ) -> None:
        super().__init__()
        self._pairs = pairs
        self._cache = cache
        self._item_store = item_store
        self._available_rarities = rarities
        self._available_crates = crates
        self._translator = translator
        self._settings_data = settings or {}
        self._worker_thread: Optional[QtCore.QThread] = None
        self._worker: Optional[ScanWorker] = None
        self._row_prices = {
            pair.index: {"slab": None, "sticker": None} for pair in self._pairs
        }
        self._item_nameids = {
            pair.index: {
                "sticker": self._lookup_item_nameid(pair.sticker_name),
                "slab": self._lookup_item_nameid(pair.slab_name),
            }
            for pair in self._pairs
        }
        self._manual_rows: Dict[int, int] = {}
        self._manual_row_pairs: Dict[int, int] = {}
        self._inventory_rows: Dict[int, int] = {}
        self._inventory_pairs: List[ItemPair] = []
        self._fullscreen_dialog: Optional[QtWidgets.QDialog] = None
        self._fullscreen_table_view: Optional[QtWidgets.QTableView] = None
        self._fullscreen_close_button: Optional[QtWidgets.QPushButton] = None
        self.setWindowTitle("Steam Sticker Scanner")
        self.resize(1100, 700)
        self._init_ui()
        self._load_settings()
        self._retranslate_ui()

    def _init_ui(self) -> None:
        self.table_model = QtGui.QStandardItemModel(0, 6)
        self.table_model.setHorizontalHeaderLabels(
            [
                self._translator.t("table_slab"),
                self._translator.t("table_sticker"),
                self._translator.t("table_slab_price"),
                self._translator.t("table_sticker_price"),
                self._translator.t("table_item_nameid"),
                self._translator.t("table_difference"),
            ]
        )
        for pair in self._pairs:
            self.table_model.appendRow(self._build_row_items(pair))

        self.proxy_model = PairFilterProxy()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseSensitivity.CaseInsensitive)

        self.table_view = QtWidgets.QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSortingEnabled(True)
        table_header = self.table_view.horizontalHeader()
        table_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        table_header.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        table_header.setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.table_view.setWordWrap(True)
        self.table_view.setStyleSheet(
            "QTableView { background-color: #0d1117; color: #c9d1d9; gridline-color: #30363d; }"
            "QHeaderView::section { background-color: #161b22; color: #58a6ff; border: none; padding: 6px; }"
        )

        self.filters_panel = FiltersPanel(self._available_rarities, self._available_crates, self._translator)
        self.filters_panel.filtersChanged.connect(self._apply_filters)

        self.fullscreen_button = QtWidgets.QPushButton()
        self.fullscreen_button.setCheckable(True)
        self.fullscreen_button.clicked.connect(self._toggle_fullscreen_table)

        self.export_button = QtWidgets.QPushButton(self._translator.t("export_button"))
        self.export_button.clicked.connect(self._export_visible_pairs)

        self.manual_model = QtGui.QStandardItemModel(0, 6)
        self.manual_model.setHorizontalHeaderLabels(
            [
                self._translator.t("table_slab"),
                self._translator.t("table_sticker"),
                self._translator.t("table_slab_price"),
                self._translator.t("table_sticker_price"),
                self._translator.t("table_item_nameid"),
                self._translator.t("table_difference"),
            ]
        )
        self.manual_table_view = QtWidgets.QTableView()
        self.manual_table_view.setModel(self.manual_model)
        manual_header = self.manual_table_view.horizontalHeader()
        manual_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        manual_header.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        manual_header.setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.manual_table_view.verticalHeader().setVisible(False)
        self.manual_table_view.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.manual_table_view.setAlternatingRowColors(True)
        self.manual_table_view.setSortingEnabled(False)
        self.manual_table_view.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.manual_table_view.setWordWrap(True)
        self.manual_table_view.setStyleSheet(
            "QTableView { background-color: #0d1117; color: #c9d1d9; gridline-color: #30363d; }"
            "QHeaderView::section { background-color: #161b22; color: #58a6ff; border: none; padding: 6px; }"
        )

        self.inventory_model = QtGui.QStandardItemModel(0, 6)
        self.inventory_model.setHorizontalHeaderLabels(
            [
                self._translator.t("table_slab"),
                self._translator.t("table_sticker"),
                self._translator.t("table_slab_price"),
                self._translator.t("table_sticker_price"),
                self._translator.t("table_item_nameid"),
                self._translator.t("table_difference"),
            ]
        )
        self.inventory_table_view = QtWidgets.QTableView()
        self.inventory_table_view.setModel(self.inventory_model)
        inventory_header = self.inventory_table_view.horizontalHeader()
        inventory_header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        inventory_header.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        inventory_header.setSectionResizeMode(
            3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.inventory_table_view.verticalHeader().setVisible(False)
        self.inventory_table_view.verticalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.inventory_table_view.setAlternatingRowColors(True)
        self.inventory_table_view.setSortingEnabled(True)
        self.inventory_table_view.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.inventory_table_view.setWordWrap(True)
        self.inventory_table_view.setStyleSheet(
            "QTableView { background-color: #0d1117; color: #c9d1d9; gridline-color: #30363d; }"
            "QHeaderView::section { background-color: #161b22; color: #58a6ff; border: none; padding: 6px; }"
        )

        self.manual_search_input = QtWidgets.QLineEdit()
        self.manual_search_input.setPlaceholderText(self._translator.t("manual_placeholder"))
        self.manual_results_list = QtWidgets.QListWidget()
        self.manual_results_list.setMaximumHeight(150)
        self.manual_results_list.setStyleSheet(
            "QListWidget { background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d; }"
            "QListWidget::item:selected { background-color: #1f6feb; color: white; }"
        )
        self.manual_search_input.textChanged.connect(self._update_manual_results)
        self.manual_search_input.returnPressed.connect(self._handle_manual_enter)
        self.manual_results_list.itemActivated.connect(self._handle_manual_result_activation)

        self._search_entries = self._build_search_entries()

        self.save_base_button = QtWidgets.QPushButton(self._translator.t("manual_save"))
        self.save_base_button.clicked.connect(self._save_manual_base)
        self.import_base_button = QtWidgets.QPushButton(self._translator.t("manual_import"))
        self.import_base_button.clicked.connect(self._import_manual_base)

        manual_controls = QtWidgets.QHBoxLayout()
        manual_controls.addWidget(self.import_base_button)
        manual_controls.addWidget(self.save_base_button)
        manual_controls.addStretch()

        manual_tab = QtWidgets.QWidget()
        manual_layout = QtWidgets.QVBoxLayout()
        self.manual_search_label = QtWidgets.QLabel(self._translator.t("manual_search"))
        manual_layout.addWidget(self.manual_search_label)
        manual_layout.addWidget(self.manual_search_input)
        manual_layout.addWidget(self.manual_results_list)
        manual_layout.addWidget(self.manual_table_view)
        manual_layout.addLayout(manual_controls)
        manual_tab.setLayout(manual_layout)
        self.manual_tab = manual_tab

        inventory_tab = QtWidgets.QWidget()
        inventory_layout = QtWidgets.QVBoxLayout()
        inventory_input_row = QtWidgets.QHBoxLayout()
        self.inventory_link_label = QtWidgets.QLabel(self._translator.t("inventory_link_label"))
        self.inventory_url_input = QtWidgets.QLineEdit()
        self.inventory_url_input.setPlaceholderText(self._translator.t("inventory_placeholder"))
        self.inventory_fetch_button = QtWidgets.QPushButton(self._translator.t("inventory_fetch"))
        self.inventory_fetch_button.clicked.connect(self._fetch_inventory_pairs)
        inventory_input_row.addWidget(self.inventory_link_label)
        inventory_input_row.addWidget(self.inventory_url_input)
        inventory_input_row.addWidget(self.inventory_fetch_button)
        self.inventory_status_label = QtWidgets.QLabel(self._translator.t("inventory_status_idle"))
        self.inventory_status_label.setStyleSheet("color: #58a6ff;")
        inventory_layout.addLayout(inventory_input_row)
        inventory_layout.addWidget(self.inventory_status_label)
        inventory_layout.addWidget(self.inventory_table_view)
        inventory_tab.setLayout(inventory_layout)
        self.inventory_tab = inventory_tab

        all_pairs_tab = QtWidgets.QWidget()
        all_layout = QtWidgets.QVBoxLayout()
        table_controls = QtWidgets.QHBoxLayout()
        table_controls.addWidget(self.fullscreen_button)
        table_controls.addWidget(self.export_button)
        table_controls.addStretch()
        all_layout.addLayout(table_controls)
        all_layout.addWidget(self.table_view)
        all_layout.addWidget(self.filters_panel)
        all_pairs_tab.setLayout(all_layout)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(all_pairs_tab, self._translator.t("tab_all_pairs"))
        self.tabs.addTab(self.manual_tab, self._translator.t("tab_selected_pairs"))
        self.tabs.addTab(self.inventory_tab, self._translator.t("tab_inventory_pairs"))

        self.settings_panel = SettingsPanel(self._translator)
        self.settings_panel.languageChanged.connect(self._change_language)

        self.status_label = QtWidgets.QLabel(self._translator.t("status_ready"))
        self.status_label.setStyleSheet("color: #58a6ff; font-weight: bold;")

        self.scan_button = QtWidgets.QPushButton(self._translator.t("scan_start"))
        self.scan_button.setCheckable(True)
        self.scan_button.clicked.connect(self._toggle_scan)
        self.scan_button.setStyleSheet(
            "QPushButton { background-color: #238636; color: white; padding: 10px; border-radius: 6px; }"
            "QPushButton:checked { background-color: #a40e26; }"
        )

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)

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
        self._apply_filters()
        self._update_manual_results("")
        self._update_fullscreen_button_text()

    def _build_row_items(self, pair: ItemPair) -> List[QtGui.QStandardItem]:
        slab_item = QtGui.QStandardItem(pair.slab_name)
        sticker_item = QtGui.QStandardItem(pair.sticker_name)
        for item in (slab_item, sticker_item):
            item.setEditable(False)
        slab_item.setData(pair.rarity_name, RARITY_ROLE)
        slab_item.setData(pair.crates, CRATES_ROLE)

        slab_price = QtGui.QStandardItem("—")
        slab_price.setEditable(False)
        slab_price.setData(None, QtCore.Qt.ItemDataRole.UserRole)
        slab_price.setData(None, SLAB_PRICE_ROLE)

        sticker_price = QtGui.QStandardItem("—")
        sticker_price.setEditable(False)
        sticker_price.setData(None, QtCore.Qt.ItemDataRole.UserRole)
        sticker_price.setData(None, STICKER_PRICE_ROLE)

        item_nameid_item = QtGui.QStandardItem(self._format_item_nameid_text(pair.index))
        item_nameid_item.setEditable(False)
        item_nameid_item.setData(
            self._item_nameids.get(pair.index, {}), ITEM_NAMEID_ROLE
        )

        difference = QtGui.QStandardItem("—")
        difference.setEditable(False)
        difference.setData(None, QtCore.Qt.ItemDataRole.UserRole)
        difference.setData(None, DIFFERENCE_ROLE)

        return [
            slab_item,
            sticker_item,
            slab_price,
            sticker_price,
            item_nameid_item,
            difference,
        ]

    def _build_search_entries(self) -> List[Dict[str, object]]:
        entries: List[Dict[str, object]] = []
        for pair in self._pairs:
            entries.append(
                {
                    "label": f"{pair.slab_name} {self._translator.t('manual_label_slab')}",
                    "search": pair.slab_name.lower(),
                    "pair_index": pair.index,
                }
            )
            entries.append(
                {
                    "label": f"{pair.sticker_name} {self._translator.t('manual_label_sticker')}",
                    "search": pair.sticker_name.lower(),
                    "pair_index": pair.index,
                }
            )
        entries.sort(key=lambda item: item["label"])
        return entries

    def _lookup_item_nameid(self, market_name: str) -> Optional[str]:
        value = self._item_store.get(market_name)
        if value:
            return value
        cached = self._cache.get_item_nameid(market_name)
        if cached:
            self._item_store.set(market_name, cached)
            return cached
        return None

    def _format_item_nameid_text(self, pair_index: int) -> str:
        item_ids = self._item_nameids.get(pair_index, {})
        sticker_id = item_ids.get("sticker")
        slab_id = item_ids.get("slab")
        parts: List[str] = []
        if sticker_id:
            parts.append(f"Sticker: {sticker_id}")
        if slab_id:
            parts.append(f"Slab: {slab_id}")
        if parts:
            return "\n".join(parts)
        return "—"

    def _format_price_text(self, price: Optional[PriceInfo]) -> str:
        buy_label = self._translator.t("price_buy")
        sell_label = self._translator.t("price_sell")
        if price is None:
            buy_text = self._translator.t("waiting_data")
            sell_text = self._translator.t("waiting_data")
        else:
            buy_text = (
                f"₴{price.buy:.2f}"
                if price.buy is not None
                else self._translator.t("waiting_data")
            )
            sell_text = (
                f"₴{price.sell:.2f}"
                if price.sell is not None
                else self._translator.t("waiting_data")
            )
        return f"{buy_label}: {buy_text}\n{sell_label}: {sell_text}"

    def _update_item_nameid_cell(
        self, model: QtGui.QStandardItemModel, row: int, pair_index: int, text: str
    ) -> None:
        item = model.item(row, 4)
        if item is None:
            item = QtGui.QStandardItem("—")
            model.setItem(row, 4, item)
        item.setText(text)
        item.setData(self._item_nameids.get(pair_index, {}), ITEM_NAMEID_ROLE)
        item.setEditable(False)

    def _apply_item_nameid_to_models(self, pair_index: int) -> None:
        text = self._format_item_nameid_text(pair_index)
        self._update_item_nameid_cell(self.table_model, pair_index, pair_index, text)
        manual_row = self._manual_rows.get(pair_index)
        if manual_row is not None:
            self._update_item_nameid_cell(self.manual_model, manual_row, pair_index, text)
        inventory_row = self._inventory_rows.get(pair_index)
        if inventory_row is not None:
            self._update_item_nameid_cell(
                self.inventory_model, inventory_row, pair_index, text
            )

    def _retranslate_ui(self) -> None:
        headers = [
            self._translator.t("table_slab"),
            self._translator.t("table_sticker"),
            self._translator.t("table_slab_price"),
            self._translator.t("table_sticker_price"),
            self._translator.t("table_item_nameid"),
            self._translator.t("table_difference"),
        ]
        self.table_model.setHorizontalHeaderLabels(headers)
        self.manual_model.setHorizontalHeaderLabels(headers)
        self.inventory_model.setHorizontalHeaderLabels(headers)
        self.filters_panel.retranslate()
        self.settings_panel.retranslate()
        self.manual_search_input.setPlaceholderText(self._translator.t("manual_placeholder"))
        self.manual_search_label.setText(self._translator.t("manual_search"))
        self.save_base_button.setText(self._translator.t("manual_save"))
        self.import_base_button.setText(self._translator.t("manual_import"))
        self.inventory_link_label.setText(self._translator.t("inventory_link_label"))
        self.inventory_url_input.setPlaceholderText(self._translator.t("inventory_placeholder"))
        self.inventory_fetch_button.setText(self._translator.t("inventory_fetch"))
        self.tabs.setTabText(0, self._translator.t("tab_all_pairs"))
        self.tabs.setTabText(1, self._translator.t("tab_selected_pairs"))
        self.tabs.setTabText(2, self._translator.t("tab_inventory_pairs"))
        self.scan_button.setText(self._translator.t("scan_stop") if self._worker_thread else self._translator.t("scan_start"))
        self.export_button.setText(self._translator.t("export_button"))
        self._update_fullscreen_button_text()
        self._update_fullscreen_dialog_text()
        self._translate_status_label()
        self._translate_inventory_status_label()
        self._search_entries = self._build_search_entries()
        self._update_manual_results(self.manual_search_input.text())
        self._refresh_difference_labels()

    def _translate_status_label(self) -> None:
        current = self.status_label.text()
        for key in (
            "status_ready",
            "status_scanning",
            "status_stopped",
            "status_add_pairs",
            "status_no_results",
        ):
            for lang, values in Translator._TRANSLATIONS.items():  # type: ignore[attr-defined]
                if current == values.get(key):
                    self.status_label.setText(self._translator.t(key))
                    return

    def _translate_inventory_status_label(self) -> None:
        current = self.inventory_status_label.text()
        for key in (
            "inventory_status_idle",
            "inventory_status_loading",
            "inventory_status_no_stickers",
            "inventory_status_no_pairs",
            "inventory_status_found",
        ):
            for lang, values in Translator._TRANSLATIONS.items():  # type: ignore[attr-defined]
                if current == values.get(key):
                    self.inventory_status_label.setText(self._translator.t(key))
                    return

    def _refresh_difference_labels(self) -> None:
        for row in range(self.table_model.rowCount()):
            self._update_difference_for_model(self.table_model, row, row)
        for row, pair_index in self._manual_row_pairs.items():
            self._update_difference_for_model(self.manual_model, row, pair_index)
        for row, pair_index in self._inventory_rows.items():
            self._update_difference_for_model(self.inventory_model, row, pair_index)

    def _change_language(self, code: str) -> None:
        self._translator.set_language(code)
        self.settings_panel._select_language(code)
        self._retranslate_ui()
        self._save_settings()

    def _update_manual_results(self, text: str) -> None:
        query = text.strip().lower()
        self.manual_results_list.clear()
        if not self._search_entries:
            return
        matches: List[Dict[str, object]] = []
        if not query:
            matches = self._search_entries[:50]
        else:
            for entry in self._search_entries:
                if query in entry["search"]:
                    matches.append(entry)
                if len(matches) >= 50:
                    break
        for entry in matches:
            item = QtWidgets.QListWidgetItem(entry["label"])
            item.setData(QtCore.Qt.ItemDataRole.UserRole, entry["pair_index"])
            self.manual_results_list.addItem(item)

    def _handle_manual_enter(self) -> None:
        item = self.manual_results_list.item(0)
        if item is not None:
            self._handle_manual_result_activation(item)

    def _handle_manual_result_activation(self, item: QtWidgets.QListWidgetItem) -> None:
        pair_index = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if pair_index is None:
            return
        try:
            pair = self._pairs[int(pair_index)]
        except (ValueError, IndexError):
            return
        self._add_manual_pair(pair)

    def _add_manual_pair(self, pair: ItemPair) -> None:
        if pair.index in self._manual_rows:
            return
        row_items = self._build_row_items(pair)
        self.manual_model.appendRow(row_items)
        row = self.manual_model.rowCount() - 1
        self._manual_rows[pair.index] = row
        self._manual_row_pairs[row] = pair.index
        self.manual_search_input.clear()
        self.manual_results_list.clear()
        self._apply_existing_prices_to_manual_row(pair.index)

    def _apply_existing_prices_to_manual_row(self, pair_index: int) -> None:
        row = self._manual_rows.get(pair_index)
        if row is None:
            return
        prices = self._row_prices.get(pair_index, {})
        updated = False
        for is_slab, key in ((True, "slab"), (False, "sticker")):
            value = prices.get(key)
            if value is not None:
                self._update_model_price_cell(
                    self.manual_model,
                    row,
                    pair_index,
                    is_slab,
                    value,
                )
                updated = True
        if updated:
            self._update_difference_for_model(self.manual_model, row, pair_index)

    def _apply_existing_prices_to_inventory_row(self, pair_index: int) -> None:
        row = self._inventory_rows.get(pair_index)
        if row is None:
            return
        prices = self._row_prices.get(pair_index, {})
        updated = False
        for is_slab, key in ((True, "slab"), (False, "sticker")):
            value = prices.get(key)
            if value is not None:
                self._update_model_price_cell(
                    self.inventory_model,
                    row,
                    pair_index,
                    is_slab,
                    value,
                )
                updated = True
        if updated:
            self._update_difference_for_model(self.inventory_model, row, pair_index)

    def _selected_pairs_for_scan(self) -> Tuple[List[ItemPair], str]:
        if self.tabs.currentWidget() == self.manual_tab:
            manual_pairs = self._collect_manual_pairs()
            return manual_pairs, "manual"
        if self.tabs.currentWidget() == self.inventory_tab:
            return list(self._inventory_pairs), "inventory"
        return self.filters_panel.filter_pairs_for_scan(self._pairs), "all"

    def _collect_manual_pairs(self) -> List[ItemPair]:
        pairs: List[ItemPair] = []
        for row in range(self.manual_model.rowCount()):
            pair_index = self._manual_row_pairs.get(row)
            if pair_index is None:
                continue
            try:
                pairs.append(self._pairs[pair_index])
            except IndexError:
                continue
        return pairs

    def _normalized_inventory_url(self, raw: str) -> Optional[str]:
        if not raw:
            return None
        url = raw.strip()
        if not url:
            return None
        if "json/730/2" in url:
            return url
        url = url.rstrip("/")
        if not url.endswith("/inventory"):
            url += "/inventory"
        return f"{url}/json/730/2?l=english&count=5000"

    def _fetch_inventory_pairs(self) -> None:
        url = self._normalized_inventory_url(self.inventory_url_input.text())
        if not url:
            self.inventory_status_label.setText(
                self._translator.t("inventory_status_error", details=self._translator.t("inventory_invalid_link"))
            )
            return
        self.inventory_status_label.setText(self._translator.t("inventory_status_loading"))
        self.inventory_fetch_button.setEnabled(False)
        session, proxies = self._inventory_request_options()
        try:
            response = session.get(url, timeout=20, proxies=proxies)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            self.inventory_status_label.setText(
                self._translator.t("inventory_status_error", details=str(exc))
            )
            self.inventory_fetch_button.setEnabled(True)
            return
        except json.JSONDecodeError:
            self.inventory_status_label.setText(
                self._translator.t("inventory_status_error", details=self._translator.t("invalid_json", name="inventory"))
            )
            self.inventory_fetch_button.setEnabled(True)
            return

        sticker_names = self._extract_stickers_from_inventory(data)
        if not sticker_names:
            self.inventory_status_label.setText(self._translator.t("inventory_status_no_stickers"))
            self.inventory_model.removeRows(0, self.inventory_model.rowCount())
            self._inventory_rows.clear()
            self._inventory_pairs = []
            self.inventory_fetch_button.setEnabled(True)
            return

        inventory_pairs: List[ItemPair] = []
        sticker_set = set(sticker_names)
        for pair in self._pairs:
            if pair.sticker_name in sticker_set:
                inventory_pairs.append(pair)

        self.inventory_model.removeRows(0, self.inventory_model.rowCount())
        self._inventory_rows.clear()
        self._inventory_pairs = inventory_pairs
        for pair in inventory_pairs:
            self.inventory_model.appendRow(self._build_row_items(pair))
            row = self.inventory_model.rowCount() - 1
            self._inventory_rows[pair.index] = row
            self._apply_existing_prices_to_inventory_row(pair.index)

        if inventory_pairs:
            self.inventory_status_label.setText(
                self._translator.t("inventory_status_found", count=len(sticker_names))
            )
        else:
            self.inventory_status_label.setText(self._translator.t("inventory_status_no_pairs"))
        self.inventory_fetch_button.setEnabled(True)

    def _inventory_request_options(self) -> Tuple[requests.Session, Optional[Dict[str, str]]]:
        settings = self.settings_panel.to_runtime_settings()
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/121.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://steamcommunity.com/",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Host": "steamcommunity.com",
            }
        )
        if settings.cookies:
            session.cookies.update(settings.cookies)
        proxy = None
        if settings.proxies:
            formatted = MarketClient._format_proxy(settings.proxies[0])
            if formatted:
                proxy = {"http": formatted, "https": formatted}
        return session, proxy

    @staticmethod
    def _extract_stickers_from_inventory(data: object) -> List[str]:
        if not isinstance(data, dict):
            return []
        inventory = data.get("rgInventory")
        descriptions = data.get("rgDescriptions")
        if not isinstance(inventory, dict) or not isinstance(descriptions, dict):
            return []
        names: List[str] = []
        for item in inventory.values():
            if not isinstance(item, dict):
                continue
            classid = item.get("classid")
            instanceid = item.get("instanceid")
            if not classid or not instanceid:
                continue
            key = f"{classid}_{instanceid}"
            description = descriptions.get(key)
            if not isinstance(description, dict):
                continue
            if not MainWindow._is_sticker_description(description):
                continue
            name = description.get("market_hash_name") or description.get("name")
            if name:
                names.append(str(name))
        return names

    @staticmethod
    def _is_sticker_description(description: Dict[str, object]) -> bool:
        tags = description.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if not isinstance(tag, dict):
                    continue
                category = str(tag.get("category") or tag.get("category_name") or "")
                name = str(tag.get("name") or tag.get("internal_name") or "")
                if category.lower() == "type" and "sticker" in name.lower():
                    return True
        desc_type = description.get("type")
        if isinstance(desc_type, str) and "sticker" in desc_type.lower():
            return True
        return False

    def _clear_manual_pairs(self) -> None:
        self.manual_model.removeRows(0, self.manual_model.rowCount())
        self._manual_rows.clear()
        self._manual_row_pairs.clear()

    def _save_manual_base(self) -> None:
        selected_pairs = self._collect_manual_pairs()
        if not selected_pairs:
            QtWidgets.QMessageBox.warning(
                self,
                self._translator.t("message_empty_list"),
                self._translator.t("message_no_pairs_to_save"),
            )
            return
        base_name, ok = QtWidgets.QInputDialog.getText(
            self,
            self._translator.t("message_base_name"),
            self._translator.t("message_enter_base_name"),
            text="my_pairs",
        )
        if not ok:
            return
        safe_name = self._sanitize_base_name(base_name)
        if not safe_name:
            QtWidgets.QMessageBox.warning(
                self,
                self._translator.t("message_error"),
                self._translator.t("message_invalid_base_name"),
            )
            return
        default_path = BASE_DIR / f"{safe_name}.json"
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self._translator.t("message_save_base"),
            str(default_path),
            "JSON (*.json)",
        )
        if not file_path:
            return
        data = {
            "name": base_name,
            "pairs": [
                {
                    "index": pair.index,
                    "sticker": pair.sticker_name,
                    "slab": pair.slab_name,
                }
                for pair in selected_pairs
            ],
        }
        try:
            Path(file_path).write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, self._translator.t("message_error"), str(exc))
            return
        QtWidgets.QMessageBox.information(
            self, self._translator.t("message_done"), self._translator.t("message_base_saved")
        )

    def _import_manual_base(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            self._translator.t("message_import_base"),
            str(BASE_DIR),
            "JSON (*.json)",
        )
        if not file_path:
            return
        try:
            data = json.loads(Path(file_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            QtWidgets.QMessageBox.critical(
                self,
                self._translator.t("message_error"),
                self._translator.t("message_file_read_error", exc=exc),
            )
            return
        pairs_data = data.get("pairs")
        if not isinstance(pairs_data, list):
            QtWidgets.QMessageBox.warning(
                self,
                self._translator.t("message_error"),
                self._translator.t("message_invalid_file"),
            )
            return
        self._clear_manual_pairs()
        missing = 0
        added = 0
        for entry in pairs_data:
            pair: Optional[ItemPair] = None
            if isinstance(entry, dict):
                idx = entry.get("index")
                if isinstance(idx, int) and 0 <= idx < len(self._pairs):
                    pair = self._pairs[idx]
                else:
                    pair = self._find_pair_by_names(
                        entry.get("sticker"), entry.get("slab")
                    )
            elif isinstance(entry, int) and 0 <= entry < len(self._pairs):
                pair = self._pairs[entry]
            if pair is None:
                missing += 1
                continue
            self._add_manual_pair(pair)
            added += 1
        message = self._translator.t("message_import_result", added=added)
        if missing:
            message += self._translator.t("message_import_skipped", missing=missing)
        QtWidgets.QMessageBox.information(self, self._translator.t("message_result"), message)

    @staticmethod
    def _sanitize_base_name(name: str) -> str:
        cleaned = re.sub(r"[^\w\- ]+", "", name, flags=re.UNICODE).strip()
        return cleaned.replace(" ", "_")

    def _find_pair_by_names(
        self, sticker_name: Optional[str], slab_name: Optional[str]
    ) -> Optional[ItemPair]:
        if not sticker_name or not slab_name:
            return None
        for pair in self._pairs:
            if pair.sticker_name == sticker_name and pair.slab_name == slab_name:
                return pair
        return None

    def _apply_price_to_models(
        self,
        pair_index: int,
        is_slab: bool,
        price: Optional[PriceInfo],
        error_text: Optional[str] = None,
    ) -> None:
        self._update_model_price_cell(
            self.table_model,
            pair_index,
            pair_index,
            is_slab,
            price,
            error_text,
        )
        manual_row = self._manual_rows.get(pair_index)
        if manual_row is not None:
            self._update_model_price_cell(
                self.manual_model,
                manual_row,
                pair_index,
                is_slab,
                price,
                error_text,
            )
        inventory_row = self._inventory_rows.get(pair_index)
        if inventory_row is not None:
            self._update_model_price_cell(
                self.inventory_model,
                inventory_row,
                pair_index,
                is_slab,
                price,
                error_text,
            )

    def _update_model_price_cell(
        self,
        model: QtGui.QStandardItemModel,
        row: int,
        pair_index: int,
        is_slab: bool,
        price: Optional[PriceInfo],
        error_text: Optional[str] = None,
    ) -> None:
        column = 2 if is_slab else 3
        role = SLAB_PRICE_ROLE if is_slab else STICKER_PRICE_ROLE
        item = model.item(row, column)
        if item is None:
            item = QtGui.QStandardItem("—")
            item.setEditable(False)
            model.setItem(row, column, item)
        if error_text is not None:
            item.setText(error_text)
        else:
            item.setText(self._format_price_text(price))
        buy_value = price.buy if price is not None else None
        sell_value = price.sell if price is not None else None
        item.setData(buy_value, QtCore.Qt.ItemDataRole.UserRole)
        item.setData(buy_value, role)
        item.setData(sell_value, SELL_PRICE_ROLE)
        item.setEditable(False)
        self._update_difference_for_model(model, row, pair_index)

    def _update_difference_for_model(
        self, model: QtGui.QStandardItemModel, row: int, pair_index: int
    ) -> None:
        item = model.item(row, 5)
        if item is None:
            item = QtGui.QStandardItem("—")
            model.setItem(row, 5, item)
        prices = self._row_prices.setdefault(pair_index, {})
        slab_price = prices.get("slab")
        sticker_price = prices.get("sticker")
        slab_buy = slab_price.buy if isinstance(slab_price, PriceInfo) else slab_price
        sticker_buy = (
            sticker_price.buy if isinstance(sticker_price, PriceInfo) else sticker_price
        )
        if slab_buy is not None and sticker_buy is not None:
            diff = slab_buy - sticker_buy
            item.setText(f"₴{diff:.2f}")
            item.setData(diff, QtCore.Qt.ItemDataRole.UserRole)
            item.setData(diff, DIFFERENCE_ROLE)
        else:
            item.setText(self._translator.t("waiting_data"))
            item.setData(None, QtCore.Qt.ItemDataRole.UserRole)
            item.setData(None, DIFFERENCE_ROLE)
        item.setEditable(False)

    def _load_settings(self) -> None:
        settings_data = self._settings_data or load_settings_file()
        self.settings_panel.load(settings_data)
        self._settings_data = settings_data

    def _save_settings(self) -> None:
        self._settings_data = self.settings_panel.export_dict()
        SETTINGS_FILE.write_text(json.dumps(self._settings_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _toggle_fullscreen_table(self) -> None:
        if self._fullscreen_dialog:
            self._fullscreen_dialog.close()
            return
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowFlag(QtCore.Qt.WindowType.Window)
        dialog.setModal(False)
        dialog.setWindowTitle(self._translator.t("tab_all_pairs"))
        layout = QtWidgets.QVBoxLayout(dialog)

        close_button = QtWidgets.QPushButton(self._translator.t("fullscreen_close"))
        close_button.clicked.connect(dialog.close)
        close_panel = QtWidgets.QWidget(dialog)
        close_panel_layout = QtWidgets.QHBoxLayout(close_panel)
        close_panel_layout.setContentsMargins(8, 8, 8, 8)
        close_panel_layout.addStretch()
        close_panel_layout.addWidget(close_button)

        table_view = QtWidgets.QTableView(dialog)
        table_view.setModel(self.proxy_model)
        table_view.setSortingEnabled(True)
        header = table_view.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table_view.verticalHeader().setVisible(False)
        table_view.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table_view.setAlternatingRowColors(True)
        table_view.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        table_view.setWordWrap(True)
        table_view.setStyleSheet(
            "QTableView { background-color: #0d1117; color: #c9d1d9; gridline-color: #30363d; }"
            "QHeaderView::section { background-color: #161b22; color: #58a6ff; border: none; padding: 6px; }"
        )

        layout.addWidget(close_panel)
        layout.addWidget(table_view)

        dialog.finished.connect(self._handle_fullscreen_closed)
        self._fullscreen_dialog = dialog
        self._fullscreen_table_view = table_view
        self._fullscreen_close_button = close_button
        self._update_fullscreen_button_text()
        self.fullscreen_button.setChecked(True)
        dialog.showFullScreen()

    def _handle_fullscreen_closed(self, _: int = 0) -> None:
        self._fullscreen_dialog = None
        self._fullscreen_table_view = None
        self._fullscreen_close_button = None
        self.fullscreen_button.setChecked(False)
        self._update_fullscreen_button_text()

    def _update_fullscreen_button_text(self) -> None:
        if hasattr(self, "fullscreen_button"):
            text = (
                self._translator.t("fullscreen_close")
                if self._fullscreen_dialog
                else self._translator.t("fullscreen_open")
            )
            self.fullscreen_button.setText(text)

    def _update_fullscreen_dialog_text(self) -> None:
        if self._fullscreen_dialog:
            self._fullscreen_dialog.setWindowTitle(self._translator.t("tab_all_pairs"))
        if self._fullscreen_close_button:
            self._fullscreen_close_button.setText(self._translator.t("fullscreen_close"))

    def _export_visible_pairs(self) -> None:
        row_count = self.proxy_model.rowCount()
        if row_count == 0:
            QtWidgets.QMessageBox.information(
                self,
                self._translator.t("message_result"),
                self._translator.t("message_export_empty"),
            )
            return

        default_path = BASE_DIR / "pairs_export.json"
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            self._translator.t("message_export_title"),
            str(default_path),
            "JSON (*.json)",
        )
        if not file_path:
            return

        exported: List[Dict[str, object]] = []
        for row in range(row_count):
            slab_name = self.proxy_model.index(row, 0).data()
            sticker_name = self.proxy_model.index(row, 1).data()
            slab_buy = self.proxy_model.index(row, 2).data(SLAB_PRICE_ROLE)
            slab_sell = self.proxy_model.index(row, 2).data(SELL_PRICE_ROLE)
            sticker_buy = self.proxy_model.index(row, 3).data(STICKER_PRICE_ROLE)
            sticker_sell = self.proxy_model.index(row, 3).data(SELL_PRICE_ROLE)
            item_nameids = self.proxy_model.index(row, 4).data(ITEM_NAMEID_ROLE) or {}
            difference = self.proxy_model.index(row, 5).data(DIFFERENCE_ROLE)
            exported.append(
                {
                    "slab": slab_name,
                    "sticker": sticker_name,
                    "slab_price": {"buy": slab_buy, "sell": slab_sell},
                    "sticker_price": {"buy": sticker_buy, "sell": sticker_sell},
                    "item_nameids": item_nameids,
                    "difference": difference,
                }
            )

        try:
            Path(file_path).write_text(
                json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except OSError as exc:
            QtWidgets.QMessageBox.critical(
                self,
                self._translator.t("message_error"),
                self._translator.t("message_export_error", error=str(exc)),
            )
            return

        QtWidgets.QMessageBox.information(
            self,
            self._translator.t("message_done"),
            self._translator.t("message_export_success", count=len(exported)),
        )

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
        scan_pairs, mode = self._selected_pairs_for_scan()
        if not scan_pairs:
            if mode == "manual":
                self.status_label.setText(self._translator.t("status_add_pairs"))
            else:
                self.status_label.setText(self._translator.t("status_no_results"))
            self.scan_button.setChecked(False)
            return
        runtime_settings = self.settings_panel.to_runtime_settings()
        client = MarketClient(self._cache, self._item_store, runtime_settings, self._translator)
        self._worker = ScanWorker(scan_pairs, client, self._translator)
        self._worker_thread = QtCore.QThread(self)
        self._worker.moveToThread(self._worker_thread)
        self._worker_thread.started.connect(self._worker.run)
        self._worker.priceUpdated.connect(self._handle_price_update)
        self._worker.priceFailed.connect(self._handle_price_failure)
        self._worker.itemIdResolved.connect(self._handle_item_nameid)
        self._worker.progressMessage.connect(self._update_status)
        self._worker.finished.connect(self._handle_finished)
        self._worker_thread.start()
        self.scan_button.setText(self._translator.t("scan_stop"))
        self.status_label.setText(self._translator.t("status_scanning"))

    def _stop_worker(self) -> None:
        if self._worker:
            self._worker.stop()
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
        self._worker = None
        self.scan_button.setChecked(False)
        self.scan_button.setText(self._translator.t("scan_start"))
        self.status_label.setText(self._translator.t("status_stopped"))
        self._cache.flush()
        self._item_store.flush()

    @QtCore.pyqtSlot(int, bool, object)
    def _handle_price_update(self, index: int, is_slab: bool, price: PriceInfo) -> None:
        key = "slab" if is_slab else "sticker"
        self._row_prices.setdefault(index, {})[key] = price
        self._apply_price_to_models(index, is_slab, price)
        self.proxy_model.invalidateFilter()

    @QtCore.pyqtSlot(int, bool, str)
    def _handle_price_failure(self, index: int, is_slab: bool, message: str) -> None:
        key = "slab" if is_slab else "sticker"
        self._row_prices.setdefault(index, {})[key] = None
        self._apply_price_to_models(index, is_slab, None, message)
        self.proxy_model.invalidateFilter()

    @QtCore.pyqtSlot(int, bool, str)
    def _handle_item_nameid(self, index: int, is_slab: bool, item_nameid: str) -> None:
        key = "slab" if is_slab else "sticker"
        entry = self._item_nameids.setdefault(index, {})
        if entry.get(key) == item_nameid:
            return
        entry[key] = item_nameid
        self._apply_item_nameid_to_models(index)

    @QtCore.pyqtSlot(str)
    def _update_status(self, message: str) -> None:
        self.status_label.setText(message)

    @QtCore.pyqtSlot()
    def _handle_finished(self) -> None:
        self._cache.flush()
        self._item_store.flush()
        self.status_label.setText(self._translator.t("status_ready"))
        self.scan_button.setChecked(False)
        self.scan_button.setText(self._translator.t("scan_start"))
        if self._worker_thread:
            self._worker_thread.quit()
            self._worker_thread.wait()
            self._worker_thread = None
        self._worker = None

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: D401
        self._stop_worker()
        super().closeEvent(event)


def load_pairs(translator: Translator) -> Tuple[List[ItemPair], List[str], List[str]]:
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
        rarity_name = (sticker.get("rarity") or {}).get("name") or translator.t("filters_unknown")
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
    settings_data = load_settings_file()
    language = str(settings_data.get("language") or Translator.DEFAULT_LANGUAGE)
    translator = Translator(language)
    pairs, rarities, crates = load_pairs(translator)
    if not pairs:
        raise SystemExit(translator.t("no_pairs_available"))
    cache = MarketCache(CACHE_FILE)
    item_store = ItemNameIdStore(ITEM_NAMEIDS_FILE)
    app = QtWidgets.QApplication([])
    window = MainWindow(pairs, cache, item_store, rarities, crates, translator, settings=settings_data)
    window.show()
    app.exec()
    cache.flush()
    item_store.flush()


if __name__ == "__main__":
    main()
