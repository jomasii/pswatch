from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Callable, Mapping

import yaml

from ps5watch.sources.aggregator import AggregatorSource
from ps5watch.sources.mercadolivre import MercadoLivreSource


def _sources_config(config_path: Path) -> dict:
    return yaml.safe_load(Path(config_path).read_text(encoding="utf-8")).get("sources", {})


def build_sources(
    config_path: Path,
    session,
    clock: Callable[[], datetime],
    data_dir: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> list:
    cfg = _sources_config(config_path)
    env = os.environ if env is None else env
    sources = []
    for name in ("zoom", "buscape"):
        urls = (cfg.get(name) or {}).get("urls") or []
        if urls:
            sources.append(AggregatorSource(name, list(urls), session, clock))

    ml = cfg.get("mercadolivre") or {}
    token = env.get("APIFY_TOKEN")
    if ml.get("enabled") and token and data_dir is not None:
        sources.append(
            MercadoLivreSource(
                token, session, clock, Path(data_dir) / "mercadolivre.json",
                windows=[(w["from"], w["until"]) for w in ml.get("windows") or []],
                interval_s=int(ml.get("interval_s", 600)),
                max_runs=int(ml.get("max_runs", 0)),
                max_items=int(ml.get("max_items", 20)),
                max_charge_usd=str(ml.get("max_charge_usd", "0.05")),
            )
        )
    return sources


def build_coupon_source(config_path: Path, session, clock: Callable[[], datetime]):
    urls = (_sources_config(config_path).get("coupons") or {}).get("urls") or {}
    if not urls:
        return None
    from ps5watch.coupons import CouponSource

    return CouponSource(dict(urls), session, clock)
