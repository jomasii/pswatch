from __future__ import annotations

from typing import Protocol

from ps5watch.models import Offer


class SourceError(Exception):
    """A fonte falhou: bloqueio, HTTP diferente de 200 ou página sem ofertas reconhecíveis."""


class Source(Protocol):
    name: str

    def fetch(self) -> list[Offer]: ...
