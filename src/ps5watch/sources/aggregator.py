from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Callable

from ps5watch.matching import match_model
from ps5watch.models import Offer
from ps5watch.sources.base import SourceError

log = logging.getLogger("ps5watch")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}
_LD_JSON = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)


def normalize_store(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def _parse_price(value) -> Decimal | None:
    """Aceita número ou texto simples ('3599.9'); ignora zero, negativo e formatos ambíguos."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str) and not re.fullmatch(r"\d+(\.\d+)?", value.strip()):
        return None
    price = Decimal(str(value))
    return price if price.is_finite() and price > 0 else None


def _product_offers(html: str) -> list[dict]:
    for block in _LD_JSON.findall(html):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        nodes = data.get("@graph", [data]) if isinstance(data, dict) else []
        for node in nodes:
            if isinstance(node, dict) and node.get("@type") == "Product":
                aggregate = node.get("offers") or {}
                return list(aggregate.get("offers") or [])
    return []


def parse_aggregator_page(html: str, source: str, now: datetime, assume_slim: bool = False) -> list[Offer]:
    """Lê as ofertas por loja do JSON-LD da página de produto (Zoom e Buscapé usam o mesmo formato)."""
    raw_offers = _product_offers(html)
    if not raw_offers:
        raise SourceError("página sem ofertas reconhecíveis (bloqueio ou layout mudou)")
    offers: dict[tuple, Offer] = {}
    for raw in raw_offers:
        try:
            model = match_model(raw.get("name", ""), assume_slim=assume_slim)
            price = _parse_price(raw.get("price"))
            if model is None or price is None or not raw.get("offeredBy"):
                continue
            offer = Offer(
                model=model,
                store=normalize_store(raw["offeredBy"]),
                price_cash=price,
                price_installment=None,
                url=raw.get("url", ""),
                source=source,
                seen_at=now,
                shipping_included=None,
            )
        except (TypeError, ValueError, AttributeError):
            log.warning("oferta ignorada por formato inesperado: %r", raw)
            continue
        offers[(offer.model, offer.store, offer.price_cash)] = offer
    return list(offers.values())


class AggregatorSource:
    def __init__(self, name: str, urls: list[str], session, clock: Callable[[], datetime]) -> None:
        self.name = name
        self._urls = urls
        self._session = session
        self._clock = clock

    def fetch(self) -> list[Offer]:
        offers: list[Offer] = []
        errors: list[str] = []
        for url in self._urls:
            try:
                response = self._session.get(url, headers=HEADERS, timeout=15)
                if response.status_code != 200:
                    raise SourceError(f"HTTP {response.status_code}")
                assume_slim = "slim" in url
                offers.extend(parse_aggregator_page(response.text, self.name, self._clock(), assume_slim))
            except SourceError as exc:
                errors.append(f"{url}: {exc}")
                log.warning("%s %s", self.name, errors[-1])
            except Exception as exc:
                errors.append(f"{url}: {exc}")
                log.warning("%s %s", self.name, errors[-1])
        if len(errors) == len(self._urls):
            raise SourceError("; ".join(errors) or "sem páginas configuradas")
        return offers
