import json
from datetime import timedelta
from decimal import Decimal

import pytest

from conftest import T0, make_offer
from ps5watch.alerts import AlertState, decide_alerts
from ps5watch.health import HealthState
from ps5watch.models import ModelKey
from ps5watch.store import DataStore, low_30d, record_history


def test_record_history_only_on_change():
    history = {}
    assert record_history(history, [make_offer(price="3900")], T0) is True
    assert record_history(history, [make_offer(price="3900")], T0 + timedelta(minutes=1)) is False
    assert record_history(history, [make_offer(price="3800")], T0 + timedelta(minutes=2)) is True
    assert len(history["slim_disc"]["kabum"]) == 2


def test_record_history_hourly_checkpoint():
    history = {}
    record_history(history, [make_offer(price="3900")], T0)
    assert record_history(history, [make_offer(price="3900")], T0 + timedelta(minutes=59)) is False
    assert record_history(history, [make_offer(price="3900")], T0 + timedelta(minutes=61)) is True


def test_record_history_stores_link_of_cheapest_offer():
    history = {}
    record_history(
        history, [make_offer(price="3900", url="https://a/1"), make_offer(price="3950", url="https://a/2")], T0
    )
    assert history["slim_disc"]["kabum"] == [[T0.isoformat(), "3900", "https://a/1"]]


def test_record_history_same_price_new_link_is_not_a_change():
    history = {}
    record_history(history, [make_offer(price="3900", url="https://a/1")], T0)
    later = T0 + timedelta(minutes=1)
    assert record_history(history, [make_offer(price="3900", url="https://a/9")], later) is False


def test_old_two_element_points_still_work():
    history = {"slim_disc": {"kabum": [[(T0 - timedelta(days=1)).isoformat(), "3800"]]}}
    assert low_30d(history, ModelKey.SLIM_DISC, T0) == Decimal("3800")
    assert record_history(history, [make_offer(price="3900")], T0) is True


def test_low_30d_ignores_older_points():
    history = {}
    record_history(history, [make_offer(price="3000")], T0 - timedelta(days=40))
    record_history(history, [make_offer(price="3900")], T0 - timedelta(days=5))
    record_history(history, [make_offer(price="3700", store="amazon")], T0 - timedelta(days=2))
    assert low_30d(history, ModelKey.SLIM_DISC, T0) == Decimal("3700")
    assert low_30d(history, ModelKey.SLIM_DIGITAL, T0) is None


class FakeRunner:
    def __init__(self, fail_push_times=0):
        self.calls = []
        self.fail_push_times = fail_push_times

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["git", "push"] and self.fail_push_times > 0:
            self.fail_push_times -= 1
            raise RuntimeError("rejected")
        return ""


def test_load_missing_files_returns_empty_state(tmp_path):
    alert, health, history = DataStore(tmp_path, FakeRunner()).load()
    assert alert == AlertState() and health == HealthState() and history == {}


def test_save_does_not_commit_when_unchanged(tmp_path):
    runner = FakeRunner()
    DataStore(tmp_path, runner).save(AlertState(), HealthState(), {}, changed=False)
    assert runner.calls == []


def test_save_commits_and_pushes_when_changed(tmp_path):
    runner = FakeRunner()
    DataStore(tmp_path, runner).save(AlertState(), HealthState(), {"x": 1}, changed=True)
    verbs = [c[1] for c in runner.calls]
    assert "commit" in verbs and "push" in verbs
    assert json.loads((tmp_path / "history.json").read_text(encoding="utf-8")) == {"x": 1}


def test_save_writes_offers_json_and_load_snapshot_reads_it(tmp_path):
    store = DataStore(tmp_path, FakeRunner())
    assert store.load_snapshot() is None
    snap = {"checked_at": T0.isoformat(), "offers": []}
    store.save(AlertState(), HealthState(), {}, changed=True, snapshot=snap)
    assert DataStore(tmp_path, FakeRunner()).load_snapshot() == snap


def test_save_without_snapshot_keeps_existing_offers_json(tmp_path):
    store = DataStore(tmp_path, FakeRunner())
    snap = {"checked_at": T0.isoformat(), "offers": []}
    store.save(AlertState(), HealthState(), {}, changed=True, snapshot=snap)
    store.save(AlertState(), HealthState(), {"x": 1}, changed=True)
    assert store.load_snapshot() == snap


def test_save_retries_push_after_conflict(tmp_path):
    runner = FakeRunner(fail_push_times=1)
    DataStore(tmp_path, runner).save(AlertState(), HealthState(), {}, changed=True)
    verbs = [c[1] for c in runner.calls]
    assert verbs.count("push") == 2
    assert "pull" in verbs


def test_state_roundtrip_preserves_max_sent(tmp_path, cfg):
    state = AlertState()
    for i in range(3):
        _, state = decide_alerts([make_offer(price="3500")], state, {}, T0 + timedelta(seconds=60 * i), cfg)
    store = DataStore(tmp_path, FakeRunner())
    store.save(state, HealthState(), {}, changed=True)
    alert, _, _ = DataStore(tmp_path, FakeRunner()).load()
    assert alert.models[ModelKey.SLIM_DISC].max_sent == 3


def test_save_raises_after_three_failed_pushes(tmp_path):
    runner = FakeRunner(fail_push_times=5)
    with pytest.raises(RuntimeError):
        DataStore(tmp_path, runner).save(AlertState(), HealthState(), {}, changed=True)
