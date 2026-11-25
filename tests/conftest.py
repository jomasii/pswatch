from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from ps5watch.config import load_config
from ps5watch.models import ModelKey, Offer

ROOT = Path(__file__).resolve().parent.parent
T0 = datetime(2026, 11, 27, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def cfg():
    return load_config(ROOT / "config.yaml")


def make_offer(model=ModelKey.SLIM_DISC, price="3950", store="kabum", **kw):
    return Offer(
        model=model,
        store=store,
        price_cash=Decimal(str(price)),
        price_installment=kw.get("price_installment"),
        url=kw.get("url", "https://example.com/ps5"),
        source=kw.get("source", "test"),
        seen_at=kw.get("seen_at", T0),
        shipping_included=kw.get("shipping_included"),
        bundle=kw.get("bundle", False),
        title=kw.get("title", ""),
    )
