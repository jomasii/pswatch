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
    # Magalu e Amazon ("Disk + Controle DualSense" = controle que já vem na caixa).
    assert [(o.store, o.price_cash) for o in sorted(offers, key=lambda o: o.price_cash)] == [
        ("magazine luiza", Decimal("4621.75")),
        ("amazon", Decimal("5199.9")),
    ]
    offer = offers[0]
    assert offer.model == ModelKey.SLIM_DISC
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


def _page_with_offers(offers: list[dict]) -> str:
    import json

    product = {"@type": "Product", "offers": {"offers": offers}}
    return '<script type="application/ld+json">' + json.dumps({"@graph": [product]}) + "</script>"


def test_parse_skips_non_positive_and_malformed_prices_but_keeps_the_rest():
    name = "Console PlayStation 5 Slim Digital 1TB"
    html = _page_with_offers(
        [
            {"name": name, "offeredBy": "Amazon", "price": 0, "url": "https://a"},
            {"name": name, "offeredBy": "KaBuM!", "price": "3.599,90", "url": "https://b"},
            {"name": name, "offeredBy": "Magazine Luiza", "price": 4000, "url": "https://c"},
        ]
    )
    offers = parse_aggregator_page(html, "zoom", T0, assume_slim=True)
    assert [o.store for o in offers] == ["magazine luiza"]


def test_parse_marks_combo_offers_and_keeps_title():
    title = "PlayStation®5 Slim Digital 825GB – Pacote ASTRO BOT e Gran Turismo 7"
    html = _page_with_offers(
        [
            {"name": title, "offeredBy": "Amazon", "price": 4599, "url": "https://a"},
            {"name": "Console PlayStation 5 Slim Digital 1TB", "offeredBy": "KaBuM!", "price": 4370.07, "url": "https://b"},
        ]
    )
    offers = {o.store: o for o in parse_aggregator_page(html, "zoom", T0, assume_slim=True)}
    assert offers["amazon"].bundle is True and offers["amazon"].title == title
    assert offers["kabum"].bundle is False


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
