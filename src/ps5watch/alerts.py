from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from typing import Literal

from ps5watch.config import Config
from ps5watch.models import ModelKey, Offer


def _dec(value: str | None) -> Decimal | None:
    return None if value is None else Decimal(value)


def _time(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


@dataclass
class ModelAlertState:
    last_alert_price: Decimal | None = None
    max_sent: int = 0
    last_max_at: datetime | None = None
    last_suspect_price: Decimal | None = None
    above_since: datetime | None = None


@dataclass
class AlertState:
    models: dict[ModelKey, ModelAlertState] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            key.value: {
                "last_alert_price": None if s.last_alert_price is None else str(s.last_alert_price),
                "max_sent": s.max_sent,
                "last_max_at": None if s.last_max_at is None else s.last_max_at.isoformat(),
                "last_suspect_price": None if s.last_suspect_price is None else str(s.last_suspect_price),
                "above_since": None if s.above_since is None else s.above_since.isoformat(),
            }
            for key, s in self.models.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AlertState":
        models = {}
        for key, s in data.items():
            models[ModelKey(key)] = ModelAlertState(
                last_alert_price=_dec(s.get("last_alert_price")),
                max_sent=int(s.get("max_sent", 0)),
                last_max_at=_time(s.get("last_max_at")),
                last_suspect_price=_dec(s.get("last_suspect_price")),
                above_since=_time(s.get("above_since")),
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
        s = new_state.models.setdefault(model, ModelAlertState())
        low = low_30d.get(model)

        def emit(kind: str, offer: Offer) -> None:
            messages.append(Message(kind=kind, model=model, offer=offer, low_30d=low))

        # Preços implausíveis viram só um aviso "suspeito"; nunca escondem as ofertas reais.
        suspects = [o for o in candidates if o.price_cash < cfg.suspect_floor]
        normals = [o for o in candidates if o.price_cash >= cfg.suspect_floor]
        if suspects:
            lowest = min(suspects, key=lambda o: o.price_cash)
            if s.last_suspect_price != lowest.price_cash:
                emit("suspect", lowest)
                s.last_suspect_price = lowest.price_cash
        else:
            s.last_suspect_price = None
        if not normals:
            continue

        best = min(normals, key=lambda o: o.price_cash)
        price = best.price_cash

        # Preço acima do último alerta (ou fora da faixa): só "rearma" depois de um tempo,
        # para que uma oferta que pisca (estoque, página fora do ar) não repita o alerta.
        above = s.last_alert_price is not None and (
            price > s.last_alert_price or price >= cfg.normal_threshold
        )
        if above:
            if s.above_since is None:
                s.above_since = now
            if (now - s.above_since).total_seconds() >= cfg.rearm_after_s:
                s.max_sent = 0
                s.last_max_at = None
                s.above_since = None
                s.last_alert_price = None if price >= cfg.normal_threshold else price
                continue
        else:
            s.above_since = None

        if price >= cfg.normal_threshold:
            continue

        is_new_low = s.last_alert_price is None or price < s.last_alert_price

        if price < cfg.max_threshold:
            if s.max_sent == 0 or is_new_low:
                emit("max", best)
                s.max_sent = 1
                s.last_max_at = now
                s.last_alert_price = price if s.last_alert_price is None else min(price, s.last_alert_price)
            elif (
                s.max_sent < cfg.max_repeats
                and s.last_max_at is not None
                and (now - s.last_max_at).total_seconds() >= cfg.max_repeat_interval_s
            ):
                emit("max", best)
                s.max_sent += 1
                s.last_max_at = now
            continue

        # faixa entre 3.600 e 4.000: alerta normal só quando bate um novo mínimo
        if is_new_low:
            emit("normal", best)
            s.last_alert_price = price

    return messages, new_state
