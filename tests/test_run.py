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


class PausedSource(FakeSource):
    def __init__(self, name, active):
        super().__init__(name, [])
        self._active = active
        self.fetches = 0
        self.dirty = False

    def active(self):
        return self._active

    def fetch(self):
        self.fetches += 1
        return super().fetch()

    def pop_dirty(self):
        dirty, self.dirty = self.dirty, False
        return dirty


def test_run_once_skips_paused_source_without_health_warning(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    paused = PausedSource("mercadolivre", active=False)
    sources = [FakeSource("zoom", [make_offer(price="4500")]), paused]
    run_once(sources, store, tg, cfg, T0)
    run_once(sources, store, tg, cfg, T0 + timedelta(minutes=11))
    assert paused.fetches == 0
    assert not any("mercadolivre" in text for text in tg.sent)


def test_run_once_saves_when_a_source_cache_changed(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    source = PausedSource("mercadolivre", active=True)
    run_once([source], store, tg, cfg, T0)
    saves = store.saves
    run_once([source], store, tg, cfg, T0 + timedelta(seconds=45))
    assert store.saves == saves  # nada mudou
    source.dirty = True
    run_once([source], store, tg, cfg, T0 + timedelta(seconds=90))
    assert store.saves == saves + 1


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


class PagedSource:
    """Fonte com várias páginas, como o Zoom: informa o erro de cada página."""

    def __init__(self, name, offers, page_errors, raise_all=False):
        self.name = name
        self._offers = offers
        self._page_errors = page_errors
        self._raise_all = raise_all
        self.page_errors = {}

    def fetch(self):
        self.page_errors = dict(self._page_errors)
        if self._raise_all:
            raise SourceError("todas as páginas falharam")
        return list(self._offers)


def test_partial_page_failure_alerts_after_10_minutes_naming_the_page(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    pages = {"https://z/console-ps5-slim-disc": None, "https://z/ps5-slim-bundle-astro": "HTTP 503"}
    source = PagedSource("zoom", [make_offer(price="4600")], pages)
    run_once([source], store, tg, cfg, T0)
    assert tg.sent == []
    run_once([source], store, tg, cfg, T0 + timedelta(minutes=10))
    assert len(tg.sent) == 1
    assert "zoom" in tg.sent[0] and "ps5-slim-bundle-astro" in tg.sent[0] and "fora do ar" in tg.sent[0]
    assert "console-ps5-slim-disc" not in tg.sent[0]


def test_total_failure_of_paged_source_sends_a_single_message(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    pages = {"https://z/a": "HTTP 403", "https://z/b": "HTTP 403", "https://z/c": "HTTP 403"}
    source = PagedSource("zoom", [], pages, raise_all=True)
    run_once([source], store, tg, cfg, T0)
    run_once([source], store, tg, cfg, T0 + timedelta(minutes=10))
    assert len(tg.sent) == 1
    assert "3 páginas" in tg.sent[0]


def test_recovered_page_sends_back_up_message(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    bad = PagedSource("zoom", [make_offer(price="4600")], {"https://z/a": None, "https://z/b": "HTTP 503"})
    run_once([bad], store, tg, cfg, T0)
    run_once([bad], store, tg, cfg, T0 + timedelta(minutes=10))
    good = PagedSource("zoom", [make_offer(price="4600")], {"https://z/a": None, "https://z/b": None})
    run_once([good], store, tg, cfg, T0 + timedelta(minutes=11))
    assert len(tg.sent) == 2 and "voltou" in tg.sent[1] and "b" in tg.sent[1]


def test_suspect_prices_are_not_recorded_in_history(cfg):
    store, tg = MemoryStore(), FakeTelegram()
    run_once([FakeSource("zoom", [make_offer(price="1500")])], store, tg, cfg, T0)
    assert store.history == {}


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
