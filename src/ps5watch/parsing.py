from __future__ import annotations

import re
from decimal import Decimal

_NUMBER = re.compile(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?")


def parse_brl(text: str) -> Decimal | None:
    """Converte textos como 'R$ 3.599,90' em Decimal; None se não houver valor."""
    match = _NUMBER.search(text or "")
    if not match:
        return None
    integer = match.group(1).replace(".", "")
    cents = match.group(2) or "0"
    return Decimal(f"{integer}.{cents}")
