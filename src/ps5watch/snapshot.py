"""Retrato das ofertas atuais (offers.json), lido pelo painel ao vivo."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from ps5watch.config import Config
from ps5watch.models import Offer

HEARTBEAT_S = 300


def _since(history: dict, offer: Offer, now: datetime) -> str:
    """Início da sequência mais recente de pontos com o preço atual daquela loja."""
    points = history.get(offer.model.value, {}).get(offer.store.lower(), [])
    since = None
    for point in reversed(points):
        if Decimal(point[1]) != offer.price_cash:
            break
        since = point[0]
    return since or now.isoformat()


def build_snapshot(offers: list[Offer], history: dict, cfg: Config, now: datetime) -> dict:
    rows: dict[tuple, dict] = {}
    for o in sorted(offers, key=lambda o: (o.price_cash, o.store)):
        if o.price_cash < cfg.suspect_floor or o.store.lower() not in cfg.allowed_stores:
            continue
        key = (o.model.value, o.store, o.price_cash, o.url)
        if key in rows:
            continue
        rows[key] = {
            "model": o.model.value,
            "store": o.store,
            "price": str(o.price_cash),
            "url": o.url,
            "bundle": o.bundle,
            "title": o.title,
            "promo": o.promo,
            "source": o.source,
            "since": _since(history, o, now),
        }
    return {"checked_at": now.isoformat(), "offers": list(rows.values())}


def snapshot_changed(old: dict | None, new: dict, now: datetime, heartbeat_s: int = HEARTBEAT_S) -> bool:
    if not old:
        return True
    # "since" acompanha o preço; comparar sem ele evita gravar só porque o relógio andou
    def strip(offers):
        return [{k: v for k, v in o.items() if k != "since"} for o in offers or []]

    if strip(old.get("offers")) != strip(new["offers"]):
        return True
    try:
        last = datetime.fromisoformat(old["checked_at"])
    except (KeyError, TypeError, ValueError):
        return True
    return (now - last).total_seconds() >= heartbeat_s
