"""Teste descartável: robôs do Apify trazem preços atuais do PS5 Slim no Mercado Livre?

Roda dois robôs com teto de gasto (maxTotalChargeUsd) e mostra, para cada oferta,
título, preço e se o nosso filtro reconheceria o modelo. Nunca imprime o token.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ps5watch.matching import classify  # noqa: E402

API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
QUERY = "playstation 5 slim"
MAX_ITEMS = 20
MAX_CHARGE_USD = "0.10"

# (robô, entrada, campo do título, campo do preço, campo do link)
ACTORS = [
    (
        "karamelo~mercadolivre-scraper-brasil-portugues",
        {"keyword": QUERY, "maxPages": 1, "promoted": False},
        "eTituloProduto", "novoPreco", "zProdutoLink",
    ),
    (
        "riseandcode~apify-mercadolivre-search",
        {"searchTerms": [QUERY], "country": "BR", "maxItems": 48, "excludeSponsored": True},
        "title", "price", "url",
    ),
]


def probe(token: str, actor: str, payload: dict, title_key: str, price_key: str, url_key: str) -> None:
    print(f"\n==================== {actor}")
    started = time.monotonic()
    try:
        r = requests.post(
            API.format(actor=actor),
            params={"maxItems": MAX_ITEMS, "maxTotalChargeUsd": MAX_CHARGE_USD, "timeout": 240},
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=280,
        )
    except requests.RequestException as exc:
        print(f"falhou: {type(exc).__name__}")
        return
    elapsed = time.monotonic() - started
    print(f"HTTP {r.status_code} em {elapsed:.0f} s")
    if r.status_code not in (200, 201):
        print(r.text[:500])
        return
    items = r.json()
    print(f"ofertas: {len(items)}")
    if items:
        print("campos:", ", ".join(sorted(items[0].keys())))
    matched = 0
    for it in items:
        title = str(it.get(title_key) or "")
        match = classify(title)
        if match:
            matched += 1
        tag = f"{match[0].value}{' +combo' if match[1] else ''}" if match else "ignorado"
        print(f"  R$ {it.get(price_key)!s:>10} | {tag:<22} | {title[:70]}")
        print(f"      {str(it.get(url_key) or '')[:120]}")
    print(f"reconhecidas pelo filtro: {matched}/{len(items)}")


def main() -> int:
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print("Falta o segredo APIFY_TOKEN.")
        return 1
    for actor in ACTORS:
        probe(token, *actor)
    return 0


if __name__ == "__main__":
    sys.exit(main())
