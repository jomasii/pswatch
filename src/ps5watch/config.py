from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Config:
    normal_threshold: Decimal
    max_threshold: Decimal
    suspect_floor: Decimal
    max_repeats: int
    max_repeat_interval_s: int
    allowed_stores: frozenset[str]
    health_after_s: int
    loop_duration_s: int
    loop_interval_s: int


def load_config(path: Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Config(
        normal_threshold=Decimal(str(raw["normal_threshold"])),
        max_threshold=Decimal(str(raw["max_threshold"])),
        suspect_floor=Decimal(str(raw["suspect_floor"])),
        max_repeats=int(raw["max_repeats"]),
        max_repeat_interval_s=int(raw["max_repeat_interval_s"]),
        allowed_stores=frozenset(s.lower() for s in raw["allowed_stores"]),
        health_after_s=int(raw["health_after_s"]),
        loop_duration_s=int(raw["loop_duration_s"]),
        loop_interval_s=int(raw["loop_interval_s"]),
    )
