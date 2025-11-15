from __future__ import annotations

import logging
from typing import List

from models import PairResult, SlabItem
from steam_client import SteamClient


SEARCH_URL = "https://steamcommunity.com/market/search/render"


def fetch_all_slabs(steam_client: SteamClient) -> List[SlabItem]:
    slabs: List[SlabItem] = []
    start = 0
    count = 100
    total_count = None
    while total_count is None or start < total_count:
        params = {
            "query": "slab",
            "appid": 730,
            "start": start,
            "count": count,
            "search_descriptions": 0,
            "sort_column": "price",
            "sort_dir": "asc",
        }
        data = steam_client.request_json(SEARCH_URL, params=params)
        if not data:
            logging.error("Failed to fetch slabs page at start %s", start)
            break
        total_count = data.get("total_count", 0)
        results = data.get("results", [])
        for item in results:
            name = item.get("hash_name", "")
            if not name.startswith("Sticker Slab |"):
                continue
            sell_price = 0.0
            try:
                sell_price = float(item.get("sell_price", 0))
            except (TypeError, ValueError):
                sell_price = 0.0
            slabs.append(SlabItem(name=name, sell_price=sell_price))
        start += count
        if not results:
            break
    return slabs


def slab_to_sticker_name(slab_name: str) -> str:
    return slab_name.replace("Sticker Slab |", "Sticker |", 1)


def analyze_pairs(
    steam_client: SteamClient,
    slabs: List[SlabItem],
    config,
    progress_callback=None,
) -> List[PairResult]:
    results: List[PairResult] = []
    total = len(slabs)
    for idx, slab in enumerate(slabs, start=1):
        sticker_name = slab_to_sticker_name(slab.name)
        try:
            slab_buy = steam_client.fetch_item_buy_order_price(slab.name)
            sticker_buy = steam_client.fetch_item_buy_order_price(sticker_name)
        except Exception as exc:  # noqa: BLE001
            logging.exception("Error fetching prices for %s", slab.name)
            results.append(
                PairResult(
                    slab_name=slab.name,
                    sticker_name=sticker_name,
                    slab_buy=None,
                    sticker_buy=None,
                    diff=None,
                    condition_matched=False,
                    condition_type=None,
                )
            )
            continue

        diff = None
        condition_matched = False
        condition_type = None
        if slab_buy is not None and sticker_buy is not None:
            diff = slab_buy - sticker_buy
            if diff >= config.diff_when_slab_more_expensive:
                condition_matched = True
                condition_type = "SLAB_MORE_EXPENSIVE"
            elif diff <= -config.diff_when_slab_cheaper:
                condition_matched = True
                condition_type = "SLAB_CHEAPER"

        results.append(
            PairResult(
                slab_name=slab.name,
                sticker_name=sticker_name,
                slab_buy=slab_buy,
                sticker_buy=sticker_buy,
                diff=diff,
                condition_matched=condition_matched,
                condition_type=condition_type,
            )
        )
        if progress_callback:
            progress_callback(idx, total)
    return results
