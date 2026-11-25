from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Callable

from ps5watch.alerts import AlertState
from ps5watch.health import HealthState
from ps5watch.models import ModelKey, Offer

CHECKPOINT = timedelta(hours=1)
PUSH_ATTEMPTS = 3


def record_history(history: dict, offers: list[Offer], now: datetime) -> bool:
    """Acrescenta pontos só quando o preço muda (ou a cada hora). Devolve True se mudou.

    Cada ponto é [hora, preço, link]; pontos antigos podem ter só [hora, preço].
    """
    cheapest: dict[tuple[str, str], Offer] = {}
    for o in offers:
        key = (o.model.value, o.store.lower())
        if key not in cheapest or o.price_cash < cheapest[key].price_cash:
            cheapest[key] = o

    changed = False
    for (model, store), offer in cheapest.items():
        points = history.setdefault(model, {}).setdefault(store, [])
        if points:
            last = points[-1]
            same = Decimal(last[1]) == offer.price_cash
            fresh = now - datetime.fromisoformat(last[0]) < CHECKPOINT
            if same and fresh:
                continue
        points.append([now.isoformat(), str(offer.price_cash), offer.url])
        changed = True
    return changed


def low_30d(history: dict, model: ModelKey, now: datetime) -> Decimal | None:
    cutoff = now - timedelta(days=30)
    prices = [
        Decimal(p[1])
        for points in history.get(model.value, {}).values()
        for p in points
        if datetime.fromisoformat(p[0]) >= cutoff
    ]
    return min(prices) if prices else None


def git_runner(repo_dir: Path) -> Callable[[list[str]], str]:
    def run(args: list[str]) -> str:
        result = subprocess.run(args, cwd=repo_dir, check=True, capture_output=True, text=True)
        return result.stdout

    return run


class DataStore:
    def __init__(self, repo_dir: Path, runner: Callable[[list[str]], str]) -> None:
        self._dir = Path(repo_dir)
        self._run = runner

    def load(self) -> tuple[AlertState, HealthState, dict]:
        state_file = self._dir / "state.json"
        history_file = self._dir / "history.json"
        alert, health = AlertState(), HealthState()
        if state_file.exists():
            raw = json.loads(state_file.read_text(encoding="utf-8"))
            alert = AlertState.from_dict(raw.get("alert", {}))
            health = HealthState.from_dict(raw.get("health", {}))
        history = json.loads(history_file.read_text(encoding="utf-8")) if history_file.exists() else {}
        return alert, health, history

    def save(self, alert: AlertState, health: HealthState, history: dict, changed: bool) -> None:
        if not changed:
            return
        (self._dir / "state.json").write_text(
            json.dumps({"alert": alert.to_dict(), "health": health.to_dict()}, indent=1), encoding="utf-8"
        )
        (self._dir / "history.json").write_text(json.dumps(history), encoding="utf-8")
        self._run(["git", "add", "-A"])
        try:
            self._run(["git", "commit", "-m", "data: update"])
        except Exception:
            return  # nada novo para gravar
        last_error: Exception | None = None
        for _ in range(PUSH_ATTEMPTS):
            try:
                self._run(["git", "push", "origin", "HEAD"])
                return
            except Exception as exc:  # conflito: atualizar e tentar de novo
                last_error = exc
                try:
                    self._run(["git", "pull", "--rebase", "origin", "data"])
                except Exception:
                    pass
        raise RuntimeError("não foi possível publicar o estado") from last_error
