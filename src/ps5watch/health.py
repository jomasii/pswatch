from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from ps5watch.config import Config


@dataclass
class SourceHealth:
    failing_since: datetime | None = None
    alerted: bool = False


@dataclass
class HealthState:
    sources: dict[str, SourceHealth] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            name: {
                "failing_since": None if h.failing_since is None else h.failing_since.isoformat(),
                "alerted": h.alerted,
            }
            for name, h in self.sources.items()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HealthState":
        return cls(
            {
                name: SourceHealth(
                    failing_since=None if h["failing_since"] is None else datetime.fromisoformat(h["failing_since"]),
                    alerted=bool(h["alerted"]),
                )
                for name, h in data.items()
            }
        )


def update_health(
    state: HealthState,
    results: dict[str, str | None],
    now: datetime,
    cfg: Config,
) -> tuple[list[tuple[str, str]], HealthState]:
    """results[nome] é None se a fonte funcionou, ou o texto do erro."""
    new = HealthState({k: replace(v) for k, v in state.sources.items()})
    events: list[tuple[str, str]] = []
    for name, error in results.items():
        h = new.sources.setdefault(name, SourceHealth())
        if error is None:
            if h.alerted:
                events.append((name, "up"))
            h.failing_since = None
            h.alerted = False
            continue
        if h.failing_since is None:
            h.failing_since = now
        if not h.alerted and (now - h.failing_since).total_seconds() >= cfg.health_after_s:
            h.alerted = True
            events.append((name, "down"))
    return events, new
