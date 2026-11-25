"""Mercado Livre via robô do Apify (karamelo), com cache em arquivo.

O robô cobra por oferta, então ele só é chamado dentro das janelas configuradas,
no máximo uma vez a cada `interval_s` e até `max_runs` vezes. Entre uma chamada e
outra, as ofertas vêm do cache (o arquivo vai junto com o estado na branch data).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from ps5watch.matching import classify
from ps5watch.models import Offer
from ps5watch.parsing import parse_brl
from ps5watch.sources.base import SourceError

log = logging.getLogger("ps5watch")

ACTOR = "karamelo~mercadolivre-scraper-brasil-portugues"
API = f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items"
NAME = "mercadolivre"
STORE = "mercado livre"
QUERY = "playstation 5 slim"
_YES = {"true", "sim", "yes", "1"}


def _price(value) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        price = Decimal(str(value)) if isinstance(value, (int, float)) else parse_brl(str(value))
    except InvalidOperation:
        return None
    return price if price is not None and price.is_finite() and price > 0 else None


def _flag(value) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _YES


def parse_items(items: list, now: datetime) -> list[Offer]:
    offers = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if _flag(item.get("eCompraInternacional")) is True or _flag(item.get("is_inStock")) is False:
            continue
        title = str(item.get("eTituloProduto") or "").strip()
        match = classify(title)
        price = _price(item.get("novoPreco"))
        if match is None or price is None:
            continue
        model, bundle = match
        offers.append(
            Offer(
                model=model, store=STORE, price_cash=price, price_installment=None,
                url=str(item.get("zProdutoLink") or ""), source=NAME, seen_at=now,
                shipping_included=None, bundle=bundle, title=title,
            )
        )
    return offers


def _offer_to_dict(o: Offer) -> dict:
    return {"model": o.model.value, "price": str(o.price_cash), "url": o.url, "bundle": o.bundle, "title": o.title}


def _offer_from_dict(d: dict, seen_at: datetime) -> Offer:
    from ps5watch.models import ModelKey

    return Offer(
        model=ModelKey(d["model"]), store=STORE, price_cash=Decimal(d["price"]), price_installment=None,
        url=d["url"], source=NAME, seen_at=seen_at, shipping_included=None,
        bundle=d.get("bundle", False), title=d.get("title", ""),
    )


def _when(value) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


class MercadoLivreSource:
    name = NAME

    def __init__(
        self, token: str, session, clock: Callable[[], datetime], cache_path: Path, *,
        windows, interval_s: int, max_runs: int, max_items: int, max_charge_usd: str,
    ) -> None:
        self._token = token
        self._session = session
        self._clock = clock
        self._cache_path = Path(cache_path)
        self._windows = [(_when(a), _when(b)) for a, b in windows]
        self._interval_s = interval_s
        self._max_runs = max_runs
        self._max_items = max_items
        self._max_charge = str(max_charge_usd)
        self._dirty = False

    def _load(self) -> dict:
        try:
            return json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save(self, cache: dict) -> None:
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf-8")
        self._dirty = True

    def pop_dirty(self) -> bool:
        dirty, self._dirty = self._dirty, False
        return dirty

    def _due(self, cache: dict, now: datetime) -> bool:
        last = cache.get("fetched_at")
        return last is None or (now - datetime.fromisoformat(last)).total_seconds() >= self._interval_s

    def active(self) -> bool:
        now = self._clock()
        if not any(start <= now < end for start, end in self._windows):
            return False
        cache = self._load()
        return cache.get("runs", 0) < self._max_runs or not self._due(cache, now)

    def fetch(self) -> list[Offer]:
        now = self._clock()
        cache = self._load()
        if not self._due(cache, now) or cache.get("runs", 0) >= self._max_runs:
            if cache.get("error"):
                raise SourceError(cache["error"])
            seen_at = datetime.fromisoformat(cache["fetched_at"]) if cache.get("fetched_at") else now
            return [_offer_from_dict(d, seen_at) for d in cache.get("offers", [])]

        cache = {"fetched_at": now.isoformat(), "runs": cache.get("runs", 0) + 1, "offers": [], "error": None}
        try:
            response = self._session.post(
                API,
                params={"maxItems": self._max_items, "maxTotalChargeUsd": self._max_charge, "timeout": 120},
                headers={"Authorization": f"Bearer {self._token}"},
                json={"keyword": QUERY, "maxPages": 1, "promoted": False},
                timeout=150,
            )
            if response.status_code not in (200, 201):
                raise SourceError(f"Apify HTTP {response.status_code}")
            items = response.json()
            if not isinstance(items, list):
                raise SourceError("resposta do Apify em formato inesperado")
            offers = parse_items(items, now)
        except Exception as exc:
            cache["error"] = exc.args[0] if isinstance(exc, SourceError) else f"Apify: {type(exc).__name__}"
            self._save(cache)
            raise SourceError(cache["error"]) from exc
        cache["offers"] = [_offer_to_dict(o) for o in offers]
        self._save(cache)
        log.info("mercadolivre: %d itens, %d ofertas de PS5 Slim (consulta %d)", len(items), len(offers), cache["runs"])
        return offers
