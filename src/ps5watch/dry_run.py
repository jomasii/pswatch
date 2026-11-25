"""Ensaio sem rede: uma fonte falsa a R$ 3.500 e um Telegram que só imprime."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ps5watch.alerts import AlertState
from ps5watch.config import load_config
from ps5watch.health import HealthState
from ps5watch.models import ModelKey, Offer
from ps5watch.run import run_once

ROOT = Path(__file__).resolve().parent.parent.parent


class _Source:
    name = "falsa"

    def __init__(self, now: datetime) -> None:
        self._now = now

    def fetch(self):
        return [
            Offer(
                model=ModelKey.SLIM_DISC,
                store="kabum",
                price_cash=Decimal("3500"),
                price_installment=Decimal("3900"),
                url="https://example.com/ps5",
                source="falsa",
                seen_at=self._now,
                shipping_included=None,
            )
        ]


class _Store:
    def __init__(self) -> None:
        self.alert, self.health, self.history = AlertState(), HealthState(), {}

    def load(self):
        return self.alert, self.health, self.history

    def save(self, alert, health, history, changed):
        if changed:
            self.alert, self.health, self.history = alert, health, history


class _Telegram:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, text: str) -> bool:
        print(text, "\n" + "-" * 40)
        self.sent.append(text)
        return True


def run_dry() -> list[str]:
    cfg = load_config(ROOT / "config.yaml")
    start = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
    store, telegram = _Store(), _Telegram()
    for seconds in (0, 30, 60):  # em 30 s ainda não repete; em 60 s repete
        now = start + timedelta(seconds=seconds)
        run_once([_Source(now)], store, telegram, cfg, now)
    return telegram.sent


if __name__ == "__main__":
    run_dry()
