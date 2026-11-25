from datetime import timedelta

from conftest import T0
from ps5watch.health import HealthState, update_health


def test_no_alert_before_10_minutes(cfg):
    state = HealthState()
    _, state = update_health(state, {"zoom": "boom"}, T0, cfg)
    events, _ = update_health(state, {"zoom": "boom"}, T0 + timedelta(minutes=9), cfg)
    assert events == []


def test_alert_after_10_minutes_once(cfg):
    state = HealthState()
    _, state = update_health(state, {"zoom": "boom"}, T0, cfg)
    events, state = update_health(state, {"zoom": "boom"}, T0 + timedelta(minutes=10), cfg)
    assert events == [("zoom", "down")]
    events, _ = update_health(state, {"zoom": "boom"}, T0 + timedelta(minutes=11), cfg)
    assert events == []


def test_recovery_alert(cfg):
    state = HealthState()
    _, state = update_health(state, {"zoom": "boom"}, T0, cfg)
    _, state = update_health(state, {"zoom": "boom"}, T0 + timedelta(minutes=10), cfg)
    events, state = update_health(state, {"zoom": None}, T0 + timedelta(minutes=12), cfg)
    assert events == [("zoom", "up")]
    events, _ = update_health(state, {"zoom": None}, T0 + timedelta(minutes=13), cfg)
    assert events == []


def test_short_failure_recovers_silently(cfg):
    state = HealthState()
    _, state = update_health(state, {"zoom": "boom"}, T0, cfg)
    events, _ = update_health(state, {"zoom": None}, T0 + timedelta(minutes=2), cfg)
    assert events == []


def test_one_source_down_alerts_even_if_others_ok(cfg):
    state = HealthState()
    results = {"zoom": "boom", "mercadolivre": None}
    _, state = update_health(state, results, T0, cfg)
    events, _ = update_health(state, results, T0 + timedelta(minutes=10), cfg)
    assert events == [("zoom", "down")]


def test_state_roundtrip(cfg):
    state = HealthState()
    _, state = update_health(state, {"zoom": "boom"}, T0, cfg)
    assert HealthState.from_dict(state.to_dict()) == state
