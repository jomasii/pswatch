from pathlib import Path

from conftest import T0
from ps5watch.sources.aggregator import AggregatorSource
from ps5watch.sources.registry import build_coupon_source, build_sources

CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"


def test_build_sources_creates_zoom_and_buscape_from_config():
    sources = build_sources(CONFIG, session=object(), clock=lambda: T0)
    assert [s.name for s in sources] == ["zoom", "buscape"]
    assert all(isinstance(s, AggregatorSource) for s in sources)


def test_build_coupon_source_is_none_when_no_urls_configured():
    assert build_coupon_source(CONFIG, session=object(), clock=lambda: T0) is None
