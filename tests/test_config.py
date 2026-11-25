from decimal import Decimal
from pathlib import Path

from ps5watch.config import load_config

ROOT = Path(__file__).resolve().parent.parent


def test_load_config_reads_spec_values():
    cfg = load_config(ROOT / "config.yaml")

    assert cfg.normal_threshold == Decimal("4000")
    assert cfg.max_threshold == Decimal("3600")
    assert cfg.suspect_floor == Decimal("2000")
    assert cfg.max_repeats == 5
    assert cfg.max_repeat_interval_s == 60
    assert cfg.health_after_s == 600
    assert cfg.loop_duration_s == 290
    assert cfg.loop_interval_s == 45
    assert "amazon" in cfg.allowed_stores
