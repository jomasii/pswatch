from __future__ import annotations

import re
import unicodedata

from ps5watch.models import ModelKey

# Palavras que desqualificam o anúncio (não é o console novo, sozinho).
EXCLUDE_WORDS = {
    "pro", "usado", "usada", "seminovo", "seminova", "controle", "capa",
    "suporte", "jogo", "jogos", "bundle", "combo", "kit", "midia",
}


def _normalize(title: str) -> str:
    text = unicodedata.normalize("NFKD", title.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def match_model(title: str) -> ModelKey | None:
    text = _normalize(title)
    if "+" in text:
        return None
    words = set(re.findall(r"[a-z0-9]+", text))
    if words & EXCLUDE_WORDS:
        return None
    is_ps5 = "ps5" in words or "playstation 5" in text
    if not is_ps5 or "slim" not in words:
        return None
    if "digital" in words or "sem leitor" in text:
        return ModelKey.SLIM_DIGITAL
    if words & {"disco", "discos", "leitor"}:
        return ModelKey.SLIM_DISC
    return None
