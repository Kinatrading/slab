from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SlabItem:
    name: str
    sell_price: float


@dataclass
class StickerItem:
    name: str
    best_buy_order: Optional[float]


@dataclass
class PairResult:
    slab_name: str
    sticker_name: str
    slab_buy: Optional[float]
    sticker_buy: Optional[float]
    diff: Optional[float]
    condition_matched: bool
    condition_type: Optional[str]
