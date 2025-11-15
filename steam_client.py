from __future__ import annotations

import json
import logging
import time
from itertools import cycle
from typing import Dict, Iterable, Optional
from urllib.parse import quote_plus

import requests

from config import AppConfig


class SteamClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self._setup_headers()
        self._apply_cookies(config.cookie_string)
        proxies = config.normalized_proxies()
        self._proxy_cycle: Optional[Iterable[str]] = cycle(proxies) if proxies else None

    def _setup_headers(self) -> None:
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript,*/*;q=0.01",
            }
        )

    def _apply_cookies(self, cookie_string: str) -> None:
        for cookie in cookie_string.split(";"):
            if "=" not in cookie:
                continue
            name, value = cookie.split("=", 1)
            name = name.strip()
            value = value.strip()
            if name:
                self.session.cookies.set(name, value)

    def _get_proxy(self) -> Optional[Dict[str, str]]:
        if not self._proxy_cycle:
            return None
        proxy = next(self._proxy_cycle)
        if not proxy:
            return None
        return {"http": proxy, "https": proxy}

    def request_json(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        retries = 3
        last_error: Optional[str] = None
        delay = self.config.request_delay_ms / 1000.0
        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=10,
                    proxies=self._get_proxy(),
                )
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}"
                    logging.warning(
                        "Steam request failed (%s) on attempt %s", last_error, attempt
                    )
                else:
                    try:
                        data = response.json()
                        return data
                    except json.JSONDecodeError as exc:
                        last_error = f"JSON decode error: {exc}"
                        snippet = response.text[:500].replace("\n", " ")
                        logging.warning(
                            "JSON parsing failed on attempt %s for %s with %s: %s. "
                            "Response snippet: %s",
                            attempt,
                            url,
                            params,
                            exc,
                            snippet,
                        )
            except requests.RequestException as exc:
                last_error = str(exc)
                logging.error("Request exception on attempt %s: %s", attempt, exc)
            finally:
                time.sleep(delay)
            time.sleep(0.5)
        logging.error("Failed to fetch %s: %s", url, last_error)
        return None

    def fetch_item_buy_order_price(self, market_hash_name: str) -> Optional[float]:
        url = (
            "https://steamcommunity.com/market/listings/730/"
            f"{quote_plus(market_hash_name)}/render/"
        )
        params = {
            "country": self.config.country,
            "language": self.config.language,
            "currency": self.config.currency_id,
        }
        data = self.request_json(url, params=params)
        if not data:
            return None
        buy_order_graph = data.get("buy_order_graph")
        if not buy_order_graph:
            return None
        first_entry = buy_order_graph[0]
        if not isinstance(first_entry, (list, tuple)) or len(first_entry) < 1:
            return None
        try:
            return float(first_entry[0])
        except (TypeError, ValueError):
            return None
