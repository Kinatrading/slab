from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

CONFIG_FILE = Path("config.json")


@dataclass
class AppConfig:
    cookie_string: str = ""
    request_delay_ms: int = 500
    proxy_list: List[str] | None = None
    country: str = "US"
    language: str = "english"
    currency_id: int = 1
    diff_when_slab_more_expensive: float = 30.0
    diff_when_slab_cheaper: float = 40.0

    def normalized_proxies(self) -> List[str]:
        return [p.strip() for p in (self.proxy_list or []) if p.strip()]


def load_config() -> AppConfig:
    if not CONFIG_FILE.exists():
        return AppConfig()

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error("Failed to load config: %s", exc)
        return AppConfig()

    proxy_list = data.get("proxy_list") or []
    return AppConfig(
        cookie_string=data.get("cookie_string", ""),
        request_delay_ms=int(data.get("request_delay_ms", 500)),
        proxy_list=proxy_list,
        country=data.get("country", "US"),
        language=data.get("language", "english"),
        currency_id=int(data.get("currency_id", 1)),
        diff_when_slab_more_expensive=float(
            data.get("diff_when_slab_more_expensive", 30.0)
        ),
        diff_when_slab_cheaper=float(data.get("diff_when_slab_cheaper", 40.0)),
    )


def save_config(config: AppConfig) -> None:
    data = asdict(config)
    data["proxy_list"] = config.normalized_proxies()
    try:
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        logging.error("Failed to save config: %s", exc)
