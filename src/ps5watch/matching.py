from __future__ import annotations

import re
import unicodedata

from ps5watch.models import ModelKey

# Palavras que desqualificam o anúncio (não é o console novo).
EXCLUDE_WORDS = {
    "pro", "usado", "usada", "seminovo", "seminova", "capa", "suporte", "double",
    "uae", "ksa", "import", "importado", "international", "internacional",
    "limitada", "limitado", "limited", "anniversary", "aniversario", "ouro",
    "skin", "adesivo", "base", "carregador", "carregamento", "recondicionado",
    "recondicionada", "vitrine", "open", "japonesa", "japones", "cabo",
    "headset", "fone", "volante", "drive",
}
# Console vendido junto com jogos: aceito, mas marcado como combo.
BUNDLE_WORDS = {"jogo", "jogos", "bundle", "combo", "pacote", "kit", "pack"}
# Se o título COMEÇA por uma destas palavras, não é o console (acessório ou jogo avulso).
ACCESSORY_FIRST_WORDS = {
    "leitor", "skin", "base", "capa", "suporte", "cabo", "controle", "controller", "jogo", "jogos",
}
# "controle" só desqualifica quando o anúncio não é de um console.
CONTROLLER_WORDS = {"controle", "controles", "controller", "dualsense"}
DISC_WORDS = {"disco", "discos", "disk", "disc", "leitor", "fisico", "fisica", "standard"}

# "+ Controle DualSense" é o controle que já vem na caixa; outro "+" indica combo.
_INCLUDED_CONTROLLER = re.compile(r"\+\s*(?:\d+\s*)?(?:controle|controller|dualsense)\b[^+,]*")
_FOR_CONSOLE = re.compile(r"\bpara (?:o |a )?(?:console|ps ?5|playstation)")


def _normalize(title: str) -> str:
    text = unicodedata.normalize("NFKD", title.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.replace("®", " ").replace("™", " ")


def classify(title: str, assume_slim: bool = False) -> tuple[ModelKey, bool] | None:
    """Devolve (modelo, é_combo) ou None se o anúncio não for um PS5 Slim novo."""
    text = _INCLUDED_CONTROLLER.sub(" ", _normalize(title))
    if _FOR_CONSOLE.search(text):
        return None
    ordered = re.findall(r"[a-z0-9]+", text)
    words = set(ordered)
    if not ordered or ordered[0] in ACCESSORY_FIRST_WORDS:
        return None
    if words & EXCLUDE_WORDS:
        return None
    if "console" not in words and words & CONTROLLER_WORDS:
        return None
    if not re.search(r"\bplaystation\s*5\b|\bps\s*5\b", text):
        return None
    if "slim" not in words and not assume_slim:
        return None
    bundle = "+" in text or bool(words & BUNDLE_WORDS)
    if "digital" in words or "sem leitor" in text:
        return ModelKey.SLIM_DIGITAL, bundle
    if words & DISC_WORDS:
        return ModelKey.SLIM_DISC, bundle
    return None


def match_model(title: str, assume_slim: bool = False) -> ModelKey | None:
    result = classify(title, assume_slim)
    return None if result is None else result[0]
