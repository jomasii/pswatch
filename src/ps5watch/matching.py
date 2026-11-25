from __future__ import annotations

import re
import unicodedata

from ps5watch.models import ModelKey

# Palavras que desqualificam o anúncio (não é o console novo, vendido sozinho).
EXCLUDE_WORDS = {
    "pro", "usado", "usada", "seminovo", "seminova", "capa", "suporte",
    "jogo", "jogos", "bundle", "combo", "kit", "pack", "pacote", "double",
    "uae", "ksa", "import", "importado", "international", "internacional",
    "limitada", "limitado", "limited", "anniversary", "aniversario", "ouro",
}
# "controle" só desqualifica quando o anúncio não é de um console.
CONTROLLER_WORDS = {"controle", "controles", "controller", "dualsense"}
DISC_WORDS = {"disco", "discos", "disk", "disc", "leitor", "fisico", "fisica", "standard"}


def _normalize(title: str) -> str:
    text = unicodedata.normalize("NFKD", title.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.replace("®", " ").replace("™", " ")


def match_model(title: str, assume_slim: bool = False) -> ModelKey | None:
    text = _normalize(title)
    if "+" in text:
        return None
    words = set(re.findall(r"[a-z0-9]+", text))
    if words & EXCLUDE_WORDS:
        return None
    if "console" not in words and words & CONTROLLER_WORDS:
        return None
    if not re.search(r"\bplaystation\s*5\b|\bps\s*5\b", text):
        return None
    if "slim" not in words and not assume_slim:
        return None
    if "digital" in words or "sem leitor" in text:
        return ModelKey.SLIM_DIGITAL
    if words & DISC_WORDS:
        return ModelKey.SLIM_DISC
    return None
