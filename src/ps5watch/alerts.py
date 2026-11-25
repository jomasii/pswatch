from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Literal

from ps5watch.config import Config
from ps5watch.models import ModelKey, Offer


@dataclass
class ModelAlertState:
    last_alert_price: Decimal | None = None
    max_sent: int = 0
    last_max_at: datetime | None = None


@dataclass
class AlertState:
    models: dict[ModelKey, ModelAlertState] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            key.value: {
                "last_alert_price": None if s.last_alert_price is None else str(s.last_alert_price),
                "max_sent": s.max_sent,
                "last_max_at": None if s.last_max_at is None else s.last_max_at.isoformat(),
            }
            for key, s in self.models.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AlertState":
        models = {}
        for key, s in data.items():
            models[ModelKey(key)] = ModelAlertState(
                last_alert_price=None if s["last_alert_price"] is None else Decimal(s["last_alert_price"]),
                max_sent=int(s["max_sent"]),
                last_max_at=None if s["last_max_at"] is None else datetime.fromisoformat(s["last_max_at"]),
            )
        return cls(models=models)


@dataclass
class Message:
    kind: Literal["normal", "max", "suspect", "health"]
    model: ModelKey | None = None
    offer: Offer | None = None
    low_30d: Decimal | None = None
    detail: str = ""


def _copy(state: AlertState) -> AlertState:
    return AlertState({k: replace(v) for k, v in state.models.items()})


def decide_alerts(
    offers: list[Offer],
    state: AlertState,
    low_30d: dict[ModelKey, Decimal | None],
    now: datetime,
    cfg: Config,
) -> tuple[list[Message], AlertState]:
    new_state = _copy(state)
    messages: list[Message] = []
    allowed = cfg.allowed_stores

    for model in ModelKey:
        candidates = [o for o in offers if o.model == model and o.store.lower() in allowed]
        if not candidates:
            continue
        best = min(candidates, key=lambda o: o.price_cash)
        price = best.price_cash
        s = new_state.models.setdefault(model, ModelAlertState())
        low = low_30d.get(model)

        def emit(kind: str) -> None:
            messages.append(Message(kind=kind, model=model, offer=best, low_30d=low))

        if price < cfg.suspect_floor:
            if s.last_alert_price != price:
                emit("suspect")
                s.last_alert_price = price
            continue

        if price >= cfg.normal_threshold:
            s.last_alert_price = None
            s.max_sent = 0
            s.last_max_at = None
            continue

        is_new_low = s.last_alert_price is None or price < s.last_alert_price

        if price < cfg.max_threshold:
            if s.max_sent == 0 or is_new_low:
                emit("max")
                s.max_sent = 1
                s.last_max_at = now
                s.last_alert_price = price
            elif (
                s.max_sent < cfg.max_repeats
                and s.last_max_at is not None
                and (now - s.last_max_at).total_seconds() >= cfg.max_repeat_interval_s
            ):
                emit("max")
                s.max_sent += 1
                s.last_max_at = now
            continue

        # faixa entre 3.600 e 4.000: alerta normal
        s.max_sent = 0
        s.last_max_at = None
        if is_new_low:
            emit("normal")
            s.last_alert_price = price
        else:
            s.last_alert_price = price  # subiu dentro da faixa: sem aviso, mas o próximo mínimo alerta

    return messages, new_state
