from datetime import timedelta

from conftest import T0, make_offer
from ps5watch.models import ModelKey
from ps5watch.snapshot import build_snapshot, snapshot_changed


def test_snapshot_filters_suspect_and_unknown_stores_and_sorts(cfg):
    offers = [
        make_offer(price="1500", store="kabum"),
        make_offer(price="3900", store="lojax"),
        make_offer(price="4100", store="kabum", url="https://k", bundle=True, title="PS5 + jogos", promo="cupom"),
        make_offer(price="3950", store="amazon", url="https://a"),
    ]
    snap = build_snapshot(offers, {}, cfg, T0)
    assert snap["checked_at"] == T0.isoformat()
    assert [(o["store"], o["price"]) for o in snap["offers"]] == [("amazon", "3950"), ("kabum", "4100")]
    kabum = snap["offers"][1]
    assert kabum == {
        "model": "slim_disc", "store": "kabum", "price": "4100", "url": "https://k", "bundle": True,
        "title": "PS5 + jogos", "promo": "cupom", "source": "test", "since": T0.isoformat(),
    }


def test_snapshot_drops_exact_duplicates(cfg):
    offers = [make_offer(price="3950", url="https://a", source="zoom"), make_offer(price="3950", url="https://a", source="buscape")]
    assert len(build_snapshot(offers, {}, cfg, T0)["offers"]) == 1


def test_snapshot_same_offer_from_zoom_and_buscape_appears_once_preferring_zoom(cfg):
    offers = [
        make_offer(price="4369.05", url="https://www.buscape.com.br/x?highlightedItemId=1", source="buscape"),
        make_offer(price="4369.05", url="https://www.zoom.com.br/x?highlightedItemId=1", source="zoom"),
    ]
    [only] = build_snapshot(offers, {}, cfg, T0)["offers"]
    assert only["source"] == "zoom"


def test_snapshot_since_uses_start_of_current_price_run(cfg):
    history = {"slim_disc": {"kabum": [
        [(T0 - timedelta(hours=3)).isoformat(), "4200", "u"],
        [(T0 - timedelta(hours=2)).isoformat(), "4100", "u"],
        [(T0 - timedelta(hours=1)).isoformat(), "4100"],
    ]}}
    snap = build_snapshot([make_offer(price="4100")], history, cfg, T0)
    assert snap["offers"][0]["since"] == (T0 - timedelta(hours=2)).isoformat()


def test_snapshot_since_is_now_when_history_has_other_price(cfg):
    history = {"slim_disc": {"kabum": [[(T0 - timedelta(hours=1)).isoformat(), "4200", "u"]]}}
    snap = build_snapshot([make_offer(price="4100")], history, cfg, T0)
    assert snap["offers"][0]["since"] == T0.isoformat()


def test_snapshot_empty_offers_still_has_checked_at(cfg):
    assert build_snapshot([], {}, cfg, T0) == {"checked_at": T0.isoformat(), "offers": []}


def test_snapshot_changed_rules(cfg):
    old = build_snapshot([make_offer(price="3950")], {}, cfg, T0)
    assert snapshot_changed(None, old, T0) is True
    same = build_snapshot([make_offer(price="3950")], {}, cfg, T0 + timedelta(seconds=60))
    assert snapshot_changed(old, same, T0 + timedelta(seconds=60)) is False
    assert snapshot_changed(old, same, T0 + timedelta(seconds=599)) is False
    assert snapshot_changed(old, same, T0 + timedelta(seconds=600)) is True
    other = build_snapshot([make_offer(price="3900")], {}, cfg, T0 + timedelta(seconds=60))
    assert snapshot_changed(old, other, T0 + timedelta(seconds=60)) is True


def test_model_value_in_snapshot_is_plain_string(cfg):
    snap = build_snapshot([make_offer(model=ModelKey.SLIM_DIGITAL, price="3950")], {}, cfg, T0)
    assert snap["offers"][0]["model"] == "slim_digital"
