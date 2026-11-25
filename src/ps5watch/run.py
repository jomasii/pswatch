from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from ps5watch.alerts import ModelAlertState, Message, decide_alerts
from ps5watch.config import Config, load_config
from ps5watch.formatting import format_message
from ps5watch.health import update_health
from ps5watch.models import ModelKey, Offer
from ps5watch.store import low_30d, record_history

log = logging.getLogger("ps5watch")


def _fetch_all(sources) -> tuple[list[Offer], dict[str, str | None]]:
    offers: list[Offer] = []
    results: dict[str, str | None] = {}
    for source in sources:
        try:
            found = source.fetch()
        except Exception as exc:  # qualquer falha da fonte vira aviso de saúde
            log.warning("fonte %s falhou: %s", source.name, exc)
            results[source.name] = str(exc) or type(exc).__name__
            continue
        if not found:
            results[source.name] = "nenhuma oferta encontrada"
            continue
        results[source.name] = None
        offers.extend(found)
    return offers, results


def run_once(sources, store, telegram, cfg: Config, now: datetime, coupon_source=None) -> None:
    alert, health, history = store.load()
    old_alert, old_health = alert.to_dict(), health.to_dict()

    offers, results = _fetch_all(sources)
    events, new_health = update_health(health, results, now, cfg)
    for name, status in events:
        telegram.send(format_message(Message(kind="health", detail=f"{name}|{status}")))

    coupons = []
    if coupon_source is not None:
        try:
            coupons = coupon_source.fetch()
        except Exception as exc:  # cupom nunca atrapalha o preço
            log.warning("cupons falharam: %s", exc)

    low = {model: low_30d(history, model, now) for model in ModelKey}
    messages, new_alert = decide_alerts(offers, alert, low, now, cfg)
    for msg in messages:
        if not telegram.send(format_message(msg, coupons)):
            # não marcar como enviado: volta o estado desse modelo para tentar de novo
            previous = alert.models.get(msg.model)
            new_alert.models[msg.model] = previous if previous is not None else ModelAlertState()

    plausible = [o for o in offers if o.price_cash >= cfg.suspect_floor]
    history_changed = record_history(history, plausible, now)
    changed = history_changed or new_alert.to_dict() != old_alert or new_health.to_dict() != old_health
    store.save(new_alert, new_health, history, changed)


def run_loop(sources, store, telegram, cfg: Config, clock, sleep, coupon_source=None) -> None:
    start = clock()
    while (clock() - start).total_seconds() < cfg.loop_duration_s:
        try:
            run_once(sources, store, telegram, cfg, clock(), coupon_source)
        except Exception:
            log.exception("erro na checagem; seguindo para a próxima")
        sleep(cfg.loop_interval_s)


def main() -> None:
    import requests

    from ps5watch.sources.registry import build_coupon_source, build_sources
    from ps5watch.store import DataStore, git_runner
    from ps5watch.telegram import TelegramClient

    logging.basicConfig(level=logging.INFO)
    missing = [v for v in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID") if not os.environ.get(v)]
    if missing:
        raise SystemExit(f"Faltam variáveis de ambiente: {', '.join(missing)}")

    root = Path(os.environ.get("PS5WATCH_ROOT", "."))
    cfg = load_config(root / "config.yaml")
    data_dir = Path(os.environ.get("PS5WATCH_DATA_DIR", "data"))
    session = requests.Session()
    telegram = TelegramClient(os.environ["TELEGRAM_TOKEN"], os.environ["TELEGRAM_CHAT_ID"], session)
    store = DataStore(data_dir, git_runner(data_dir))
    sources = build_sources(root / "config.yaml", session, lambda: datetime.now(timezone.utc))
    coupons = build_coupon_source(root / "config.yaml", session, lambda: datetime.now(timezone.utc))
    run_loop(sources, store, telegram, cfg, lambda: datetime.now(timezone.utc), time.sleep, coupons)


if __name__ == "__main__":
    main()
