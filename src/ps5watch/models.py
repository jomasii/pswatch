from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class ModelKey(str, Enum):
    SLIM_DISC = "slim_disc"
    SLIM_DIGITAL = "slim_digital"


@dataclass(frozen=True)
class Offer:
    model: ModelKey
    store: str
    price_cash: Decimal
    price_installment: Decimal | None
    url: str
    source: str
    seen_at: datetime
    shipping_included: bool | None = None
    bundle: bool = False  # console vendido junto com jogos
    title: str = ""


@dataclass(frozen=True)
class Coupon:
    store: str
    code: str
    description: str
    source_url: str
    seen_at: datetime
