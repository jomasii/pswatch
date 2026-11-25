"""Consulta as fontes reais uma vez e imprime as ofertas (sem Telegram, sem gravar nada)."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ps5watch.config import load_config  # noqa: E402
from ps5watch.formatting import brl  # noqa: E402
from ps5watch.sources.registry import build_sources  # noqa: E402


def main() -> None:
    cfg = load_config(ROOT / "config.yaml")
    sources = build_sources(ROOT / "config.yaml", requests.Session(), lambda: datetime.now(timezone.utc))
    for source in sources:
        try:
            offers = source.fetch()
        except Exception as exc:
            print(f"[{source.name}] FALHOU: {exc}")
            continue
        print(f"[{source.name}] {len(offers)} ofertas")
        for o in sorted(offers, key=lambda o: (o.model.value, o.price_cash)):
            ok = "ok " if o.store in cfg.allowed_stores else "FORA"
            print(f"  {ok} {o.model.value:13} {brl(o.price_cash):>12}  {o.store}")


if __name__ == "__main__":
    main()
