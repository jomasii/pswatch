"""Teste descartável: o catálogo do Mercado Livre devolve preços do PS5 Slim?

Usa um token de aplicativo (client_credentials). Nunca imprime o token nem o segredo.
"""
from __future__ import annotations

import json
import os
import sys

import requests

API = "https://api.mercadolibre.com"
QUERY = "playstation 5 slim"


def show(label: str, response: requests.Response, limit: int = 600) -> None:
    body = response.text[:limit].replace("\n", " ")
    print(f"\n== {label}: HTTP {response.status_code}\n{body}")


def main() -> int:
    client_id = os.environ.get("ML_CLIENT_ID")
    secret = os.environ.get("ML_CLIENT_SECRET")
    if not client_id or not secret:
        print("Faltam os segredos ML_CLIENT_ID / ML_CLIENT_SECRET.")
        return 1

    s = requests.Session()
    r = s.post(
        f"{API}/oauth/token",
        data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": secret},
        timeout=20,
    )
    print(f"== token: HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text[:400])
        return 1
    token = r.json()["access_token"]
    s.headers["Authorization"] = f"Bearer {token}"

    show("busca pública /sites/MLB/search", s.get(f"{API}/sites/MLB/search", params={"q": QUERY, "limit": 3}, timeout=20))

    r = s.get(f"{API}/products/search", params={"status": "active", "site_id": "MLB", "q": QUERY}, timeout=20)
    show("catálogo /products/search", r, limit=300)
    if r.status_code != 200:
        return 0
    products = r.json().get("results", [])[:6]
    print(f"\nprodutos encontrados: {len(products)}")
    for p in products:
        pid = p.get("id")
        print(f"\n--- {pid} | {p.get('name')}")
        d = s.get(f"{API}/products/{pid}", timeout=20)
        print(f"detalhe: HTTP {d.status_code}")
        if d.status_code == 200:
            data = d.json()
            print("buy_box_winner:", json.dumps(data.get("buy_box_winner"), ensure_ascii=False)[:400])
        items = s.get(f"{API}/products/{pid}/items", timeout=20)
        print(f"ofertas /items: HTTP {items.status_code}")
        if items.status_code == 200:
            for it in items.json().get("results", [])[:3]:
                print("  ", it.get("price"), it.get("seller_id"), it.get("condition"), it.get("item_id"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
