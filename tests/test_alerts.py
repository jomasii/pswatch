from datetime import timedelta

from conftest import T0, make_offer
from ps5watch.alerts import AlertState, decide_alerts
from ps5watch.models import ModelKey

NO_LOW = {}


def run(offers, state, now, cfg):
    return decide_alerts(offers, state, NO_LOW, now, cfg)


def kinds(msgs):
    return [m.kind for m in msgs]


def test_below_4000_alerts_once(cfg):
    state = AlertState()
    msgs, state = run([make_offer(price="3950")], state, T0, cfg)
    assert kinds(msgs) == ["normal"]
    msgs, state = run([make_offer(price="3950")], state, T0 + timedelta(seconds=45), cfg)
    assert msgs == []


def test_lower_price_alerts_again(cfg):
    state = AlertState()
    _, state = run([make_offer(price="3950")], state, T0, cfg)
    msgs, _ = run([make_offer(price="3900")], state, T0 + timedelta(seconds=45), cfg)
    assert kinds(msgs) == ["normal"]


def test_rise_above_then_drop_alerts_again(cfg):
    state = AlertState()
    _, state = run([make_offer(price="3950")], state, T0, cfg)
    msgs, state = run([make_offer(price="4100")], state, T0 + timedelta(seconds=45), cfg)
    assert msgs == []
    msgs, _ = run([make_offer(price="3950")], state, T0 + timedelta(seconds=90), cfg)
    assert kinds(msgs) == ["normal"]


def test_below_3600_sends_max_and_repeats_up_to_5(cfg):
    state = AlertState()
    sent = 0
    for i in range(10):
        msgs, state = run([make_offer(price="3500")], state, T0 + timedelta(seconds=60 * i), cfg)
        assert all(k == "max" for k in kinds(msgs))
        sent += len(msgs)
    assert sent == 5


def test_max_repeat_waits_for_interval(cfg):
    state = AlertState()
    msgs, state = run([make_offer(price="3500")], state, T0, cfg)
    assert kinds(msgs) == ["max"]
    msgs, state = run([make_offer(price="3500")], state, T0 + timedelta(seconds=30), cfg)
    assert msgs == []


def test_max_repeat_resets_on_new_lower_price(cfg):
    state = AlertState()
    for i in range(6):
        _, state = run([make_offer(price="3500")], state, T0 + timedelta(seconds=60 * i), cfg)
    msgs, _ = run([make_offer(price="3400")], state, T0 + timedelta(seconds=400), cfg)
    assert kinds(msgs) == ["max"]


def test_each_model_independent(cfg):
    offers = [
        make_offer(model=ModelKey.SLIM_DISC, price="3500"),
        make_offer(model=ModelKey.SLIM_DIGITAL, price="3900"),
    ]
    msgs, _ = run(offers, AlertState(), T0, cfg)
    by_model = {m.model: m.kind for m in msgs}
    assert by_model == {ModelKey.SLIM_DISC: "max", ModelKey.SLIM_DIGITAL: "normal"}


def test_price_at_threshold_does_not_alert(cfg):
    msgs, _ = run([make_offer(price="4000")], AlertState(), T0, cfg)
    assert msgs == []
    msgs, _ = run([make_offer(price="3600")], AlertState(), T0, cfg)
    assert kinds(msgs) == ["normal"]


def test_suspect_price_below_2000_is_not_max(cfg):
    msgs, _ = run([make_offer(price="1500")], AlertState(), T0, cfg)
    assert kinds(msgs) == ["suspect"]


def test_store_not_allowed_is_ignored(cfg):
    msgs, _ = run([make_offer(price="3000", store="lojinha xyz")], AlertState(), T0, cfg)
    assert msgs == []


def test_rise_within_band_then_new_low_alerts(cfg):
    state = AlertState()
    _, state = run([make_offer(price="3900")], state, T0, cfg)
    msgs, state = run([make_offer(price="3950")], state, T0 + timedelta(seconds=45), cfg)
    assert msgs == []
    msgs, _ = run([make_offer(price="3920")], state, T0 + timedelta(seconds=90), cfg)
    assert kinds(msgs) == ["normal"]


def test_state_roundtrip_preserves_max_sent(cfg):
    state = AlertState()
    for i in range(3):
        _, state = run([make_offer(price="3500")], state, T0 + timedelta(seconds=60 * i), cfg)
    restored = AlertState.from_dict(state.to_dict())
    assert restored == state
    assert restored.models[ModelKey.SLIM_DISC].max_sent == 3
