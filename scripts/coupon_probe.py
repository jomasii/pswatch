"""Teste descartável: Pelando e Amazon abrem a partir do GitHub Actions? Mostram cupons?"""
from __future__ import annotations

import json
import re
import sys

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
BLOCK_MARKERS = ("captcha", "robot check", "não é um robô", "nao e um robo", "access denied", "cloudflare")


def fetch(session: requests.Session, url: str) -> str | None:
    try:
        r = session.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as exc:
        print(f"\n== {url}\nfalhou: {type(exc).__name__}")
        return None
    html = r.text
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    blocked = [m for m in BLOCK_MARKERS if m in html.lower()]
    print(f"\n== {url}\nHTTP {r.status_code} | {len(html)} bytes | título: {(title.group(1).strip() if title else '-')[:90]}")
    print(f"sinais de bloqueio: {blocked or 'nenhum'}")
    return html if r.status_code == 200 else None


def snippets(html: str, pattern: str, limit: int = 6) -> None:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    found = [m.group(0) for m in re.finditer(rf".{{0,70}}{pattern}.{{0,70}}", text, re.I)][:limit]
    print(f"trechos com /{pattern}/: {len(found)}")
    for s in found:
        print("  ·", s.strip())


def pelando(session: requests.Session) -> None:
    for url in ("https://www.pelando.com.br/busca/ps5", "https://www.pelando.com.br/busca/playstation-5"):
        html = fetch(session, url)
        if not html:
            continue
        snippets(html, r"cupom")
        snippets(html, r"PS5|PlayStation ?5", limit=8)
        data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if data:
            try:
                parsed = json.loads(data.group(1))
                print("__NEXT_DATA__ chaves:", list(parsed.get("props", {}).get("pageProps", {}).keys())[:15])
            except ValueError:
                print("__NEXT_DATA__ presente, mas não é JSON válido")


def amazon(session: requests.Session) -> None:
    html = fetch(session, "https://www.amazon.com.br/s?k=playstation+5+slim")
    asins = []
    if html:
        asins = list(dict.fromkeys(re.findall(r'data-asin="([A-Z0-9]{10})"', html)))
        print("ASINs na busca:", asins[:10])
        snippets(html, r"cupom")
    for asin in asins[:3]:
        page = fetch(session, f"https://www.amazon.com.br/dp/{asin}")
        if page:
            snippets(page, r"PlayStation", limit=2)
            snippets(page, r"cupom")


def main() -> int:
    session = requests.Session()
    pelando(session)
    amazon(session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
