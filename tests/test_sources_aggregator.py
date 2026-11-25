from decimal import Decimal
from pathlib import Path

import pytest

from conftest import T0
from ps5watch.models import ModelKey
from ps5watch.sources.aggregator import AggregatorSource, parse_aggregator_page
from ps5watch.sources.base import SourceError

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text="", status=200):
        self.text = text
        self.status_code = status


class FakeSession:
    def __init__(self, pages):
        self.pages = pages  # url -> FakeResponse
        self.requested = []

    def get(self, url, headers=None, timeout=None):
        self.requested.append(url)
        return self.pages[url]


def test_parse_zoom_disc_page_returns_matching_store_offers():
    offers = parse_aggregator_page(fixture("zoom_slim_disc.html"), "zoom", T0, assume_slim=True)
    assert len(offers) == 1
    offer = offers[0]
    assert offer.model == ModelKey.SLIM_DISC
    assert offer.store == "magazine luiza"
    assert offer.price_cash == Decimal("4621.75")
    assert offer.url.startswith("http")
    assert offer.source == "zoom"


def test_parse_zoom_digital_page_returns_digital_offers():
    offers = parse_aggregator_page(fixture("zoom_slim_digital.html"), "zoom", T0, assume_slim=True)
    assert {o.model for o in offers} == {ModelKey.SLIM_DIGITAL}
    assert {o.store for o in offers} == {"kabum", "magazine luiza"}
    assert min(o.price_cash for o in offers) == Decimal("4370.07")


def test_parse_buscape_page_uses_same_structure():
    offers = parse_aggregator_page(fixture("buscape_slim_disc.html"), "buscape", T0, assume_slim=True)
    assert offers and all(o.source == "buscape" for o in offers)


def test_parse_page_without_offers_raises_source_error():
    with pytest.raises(SourceError):
        parse_aggregator_page(fixture("blocked.html"), "zoom", T0, assume_slim=True)


def test_fetch_non_200_raises_source_error():
    session = FakeSession({"https://z/a": FakeResponse(status=403)})
    source = AggregatorSource("zoom", ["https://z/a"], session, lambda: T0)
    with pytest.raises(SourceError):
        source.fetch()


def test_fetch_returns_offers_from_all_pages_and_survives_one_bad_page():
    session = FakeSession(
        {
            "https://z/disc": FakeResponse(fixture("zoom_slim_disc.html")),
            "https://z/digital": FakeResponse(fixture("zoom_slim_digital.html")),
            "https://z/bad": FakeResponse(status=500),
        }
    )
    source = AggregatorSource("zoom", ["https://z/disc", "https://z/digital", "https://z/bad"], session, lambda: T0)
    models = {o.model for o in source.fetch()}
    assert models == {ModelKey.SLIM_DISC, ModelKey.SLIM_DIGITAL}


def test_fetch_all_pages_failing_raises_source_error():
    session = FakeSession({"https://z/a": FakeResponse(fixture("blocked.html"))})
    with pytest.raises(SourceError):
        AggregatorSource("zoom", ["https://z/a"], session, lambda: T0).fetch()
