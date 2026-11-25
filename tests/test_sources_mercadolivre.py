from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from conftest import T0
from ps5watch.models import ModelKey
from ps5watch.sources.base import SourceError
from ps5watch.sources.mercadolivre import MercadoLivreSource, parse_items

ITEMS = [
    {"eTituloProduto": "Console PlayStation® 5 Slim Edição Digital 825 GB Branco - Sony", "novoPreco": 3899,
     "zProdutoLink": "https://www.mercadolivre.com.br/a/p/MLB1", "eCompraInternacional": False, "is_inStock": True},
    {"eTituloProduto": "Console PlayStation5 Slim Disk - Pacote ASTRO BOT e Gran Turismo 7", "novoPreco": "4.844,50",
     "zProdutoLink": "https://www.mercadolivre.com.br/b/p/MLB2"},
    {"eTituloProduto": "Unidade De Disco Playstation 5 Slim Cor Branco", "novoPreco": 659,
     "zProdutoLink": "https://www.mercadolivre.com.br/c"},
    {"eTituloProduto": "Console PlayStation 5 Slim Digital 825GB", "novoPreco": 3500,
     "zProdutoLink": "https://www.mercadolivre.com.br/d", "eCompraInternacional": True},
    {"eTituloProduto": "Console PlayStation 5 Slim Digital 825GB", "novoPreco": 3400,
     "zProdutoLink": "https://www.mercadolivre.com.br/e", "is_inStock": False},
    {"eTituloProduto": "Console PlayStation 5 Slim Digital 825GB", "novoPreco": None,
     "zProdutoLink": "https://www.mercadolivre.com.br/f"},
]


def test_parse_items_keeps_ps5_slim_and_skips_parts_imports_and_out_of_stock():
    offers = parse_items(ITEMS, T0)
    assert [(o.model, o.bundle, o.price_cash) for o in offers] == [
        (ModelKey.SLIM_DIGITAL, False, Decimal("3899")),
        (ModelKey.SLIM_DISC, True, Decimal("4844.50")),
    ]
    assert all(o.store == "mercado livre" and o.source == "mercadolivre" for o in offers)
    assert offers[1].title.startswith("Console PlayStation5 Slim Disk")


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.text = str(body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kw):
        self.calls.append((url, kw))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


WINDOWS = [(T0 - timedelta(hours=1), T0 + timedelta(hours=1))]


def make_source(tmp_path, session, now, **kw):
    clock = {"now": now}
    params = dict(windows=WINDOWS, interval_s=600, max_runs=3, max_items=20, max_charge_usd="0.05")
    params.update(kw)
    source = MercadoLivreSource("tok", session, lambda: clock["now"], tmp_path / "mercadolivre.json", **params)
    return source, clock


def test_fetch_calls_apify_once_per_interval_and_reuses_cache(tmp_path):
    session = FakeSession(FakeResponse(201, ITEMS[:1]))
    source, clock = make_source(tmp_path, session, T0)
    assert source.active()
    assert len(source.fetch()) == 1
    assert source.pop_dirty() is True
    assert source.pop_dirty() is False
    url, kw = session.calls[0]
    assert "karamelo~mercadolivre-scraper-brasil-portugues" in url
    assert kw["headers"]["Authorization"] == "Bearer tok"
    assert kw["params"]["maxItems"] == 20 and kw["params"]["maxTotalChargeUsd"] == "0.05"
    assert kw["json"]["keyword"] == "playstation 5 slim"

    clock["now"] = T0 + timedelta(minutes=5)
    assert len(source.fetch()) == 1  # do cache
    assert len(session.calls) == 1

    # cache sobrevive a uma nova execução (novo objeto, mesmo arquivo)
    again, clock2 = make_source(tmp_path, session, T0 + timedelta(minutes=6))
    assert [o.price_cash for o in again.fetch()] == [Decimal("3899")]
    assert len(session.calls) == 1

    clock["now"] = T0 + timedelta(minutes=11)
    source.fetch()
    assert len(session.calls) == 2


def test_inactive_outside_windows_and_after_max_runs(tmp_path):
    session = FakeSession(FakeResponse(201, ITEMS[:1]))
    source, clock = make_source(tmp_path, session, T0 - timedelta(hours=2))
    assert not source.active()
    clock["now"] = T0 + timedelta(hours=1)  # fim é exclusivo
    assert not source.active()

    source, clock = make_source(tmp_path, session, T0, max_runs=2, interval_s=60)
    for minute in (0, 2, 4):
        clock["now"] = T0 + timedelta(minutes=minute)
        if source.active():
            source.fetch()
    assert len(session.calls) == 2
    assert not source.active()


@pytest.mark.parametrize("response", [FakeResponse(402, {"error": "sem crédito"}), TimeoutError("lento")])
def test_fetch_failure_raises_and_is_not_retried_before_interval(tmp_path, response):
    session = FakeSession(response)
    source, clock = make_source(tmp_path, session, T0)
    with pytest.raises(SourceError):
        source.fetch()
    clock["now"] = T0 + timedelta(minutes=3)
    with pytest.raises(SourceError):
        source.fetch()
    assert len(session.calls) == 1


def test_each_window_can_have_its_own_interval(tmp_path):
    session = FakeSession(FakeResponse(201, ITEMS[:1]))
    windows = [
        (T0 - timedelta(hours=1), T0 + timedelta(hours=1), 1200),
        (T0 + timedelta(hours=1), T0 + timedelta(days=1), 4 * 3600),
    ]
    source, clock = make_source(tmp_path, session, T0, windows=windows, max_runs=99)
    for minutes in (0, 10, 20, 40):  # janela 1: a cada 20 min
        clock["now"] = T0 + timedelta(minutes=minutes)
        source.fetch()
    assert len(session.calls) == 3
    for hours in (1.5, 3, 4.7):  # janela 2: a cada 4 h (última foi T0+40min)
        clock["now"] = T0 + timedelta(hours=hours)
        source.fetch()
    assert len(session.calls) == 4


def test_windows_parse_iso_strings(tmp_path):
    session = FakeSession(FakeResponse(201, []))
    source, _ = make_source(
        tmp_path, session, datetime(2026, 11, 27, 3, 30, tzinfo=timezone.utc),
        windows=[("2026-11-27T00:00:00-03:00", "2026-11-28T00:00:00-03:00")],
    )
    assert source.active()
