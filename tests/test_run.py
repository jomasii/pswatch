from datetime import timedelta
from decimal import Decimal

from conftest import T0, make_offer
from ps5watch.alerts import AlertState
from ps5watch.health import HealthState
from ps5watch.models import Coupon, ModelKey
from ps5watch.run import run_loop, run_once
from ps5watch.sources.base import SourceError


class FakeSource:
    def __init__(self, name, offers=None, error=None):
        self.name = name
        self._offers = offers or []
        self._error = error

    def fetch(self):
        if self._error:
            raise self._error
        return list(self._offers)


class FakeCoupons:
    def __init__(self, coupons):
        self._coupons = coupons

    def fetch(self):
        return list(self._coupons)


class MemoryStore:
    def __init__(self):
        self.alert, self.health, self.history = AlertState(), HealthState(), {}
        self.saves = 0

    def load(self):
        return self.alert, self.health, self.history

    def save(self, alert, health, history, changed):
        if changed:
            self.alert, self.health, self.history = alert, health, history
            self.saves += 1


class FakeTelegram:
    def __init__(self, ok=True):
        self.ok = ok
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return self.ok


def test_run_once_sends_alert_and_marks_sent_only_if_telegram_ok(cfg):
    store, tg = MemoryStore(), FakeTelegram(ok=False)
    sources = [FakeSource("zoom", [make_offer(price="3900")])]
    run_once(sources, store, tg, cfg, T0)
    assert len(tg.sent) == 1
    tg.ok = True
    run_once(sources, store, tg, cfg, T0 + timedelta(seconds=45))
    assert len(tg.sent) == 2  # reenviado porque o primeiro envio falhou
    run_once(sources, store, tg, cfg, T0 + timedelta(seconds=90))
    assert len(tg.sent) == 2  # agora marcado como enviado


def test_run_once_empty_source_result_counts_as_health_failure(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    sources = [FakeSource("zoom", [])]
    run_once(sources, store, tg, cfg, T0)
    run_once(sources, store, tg, cfg, T0 + timedelta(minutes=10))
    assert any("zoom" in text and "fora do ar" in text for text in tg.sent)


def test_run_once_continues_when_one_source_raises(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    sources = [
        FakeSource("zoom", error=SourceError("bloqueado")),
        FakeSource("mercadolivre", [make_offer(price="3900")]),
    ]
    run_once(sources, store, tg, cfg, T0)
    assert len(tg.sent) == 1
    assert "R$ 3.900,00" in tg.sent[0]


def test_run_once_persists_state_between_calls_so_repeats_not_restarted(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    sources = [FakeSource("zoom", [make_offer(price="3500")])]
    for i in range(10):
        run_once(sources, store, tg, cfg, T0 + timedelta(seconds=60 * i))
    assert len(tg.sent) == 5


def test_coupon_does_not_change_thresholds(cfg):
    coupon = Coupon(store="kabum", code="BF10", description="10% off", source_url="u", seen_at=T0)
    store, tg = MemoryStore(), FakeTelegram()
    sources = [FakeSource("zoom", [make_offer(price="4100")])]
    run_once(sources, store, tg, cfg, T0, coupon_source=FakeCoupons([coupon]))
    assert tg.sent == []

    sources = [FakeSource("zoom", [make_offer(price="3950")])]
    run_once(sources, store, tg, cfg, T0 + timedelta(seconds=45), coupon_source=FakeCoupons([coupon]))
    assert len(tg.sent) == 1 and "Cupom ativo: BF10" in tg.sent[0]


def test_low_30d_uses_history_before_this_check(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    run_once([FakeSource("zoom", [make_offer(price="4200")])], store, tg, cfg, T0)
    run_once([FakeSource("zoom", [make_offer(price="3900")])], store, tg, cfg, T0 + timedelta(minutes=2))
    assert "R$ 4.200,00" in tg.sent[0]


def test_run_loop_runs_expected_number_of_iterations(cfg):
    clock_time = [T0]
    calls = []

    def clock():
        return clock_time[0]

    def sleep(seconds):
        clock_time[0] += timedelta(seconds=seconds)

    class CountingSource:
        name = "zoom"

        def fetch(self):
            calls.append(clock_time[0])
            return [make_offer(price="4500")]

    run_loop([CountingSource()], MemoryStore(), FakeTelegram(), cfg, clock, sleep)
    assert len(calls) == 7
