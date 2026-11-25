from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

import yaml

from ps5watch.sources.aggregator import AggregatorSource


def _sources_config(config_path: Path) -> dict:
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8")).get("sources", {})


def build_sources(config_path: Path, session, clock: Callable[[], datetime]) -> list:
    cfg = _sources_config(config_path)
    sources = []
    for name in ("zoom", "buscape"):
        urls = (cfg.get(name) or {}).get("urls") or []
        if urls:
            sources.append(AggregatorSource(name, list(urls), session, clock))
    return sources


def build_coupon_source(config_path: Path, session, clock: Callable[[], datetime]):
    urls = (_sources_config(config_path).get("coupons") or {}).get("urls") or {}
    if not urls:
        return None
    from ps5watch.coupons import CouponSource

    return CouponSource(dict(urls), session, clock)
