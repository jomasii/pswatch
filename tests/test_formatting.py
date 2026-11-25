from decimal import Decimal

from conftest import T0, make_offer
from ps5watch.alerts import Message
from ps5watch.formatting import brl, format_message
from ps5watch.models import Coupon, ModelKey


def _msg(kind="max", low=Decimal("3999.00"), **offer_kw):
    offer = make_offer(price="3499", price_installment=Decimal("3899"), **offer_kw)
    return Message(kind=kind, model=offer.model, offer=offer, low_30d=low)


def test_brl_formats_thousands_and_cents():
    assert brl(Decimal("3499")) == "R$ 3.499,00"
    assert brl(Decimal("3599.9")) == "R$ 3.599,90"


def test_format_max_message_contains_required_fields():
    text = format_message(_msg(shipping_included=True))
    assert "ALERTA MÁXIMO" in text
    assert "PS5 Slim com leitor" in text
    assert "kabum" in text.lower()
    assert "R$ 3.499,00" in text
    assert "R$ 3.899,00" in text
    assert "menor preço dos últimos 30 dias" in text
    assert "R$ 3.999,00" in text
    assert "https://example.com/ps5" in text


def test_format_digital_model_name():
    offer = make_offer(model=ModelKey.SLIM_DIGITAL, price="3500")
    text = format_message(Message(kind="normal", model=offer.model, offer=offer))
    assert "PS5 Slim Digital" in text


def test_format_without_history_says_sem_historico_ainda():
    text = format_message(_msg(low=None))
    assert "sem histórico ainda" in text


def test_format_flags_shipping_not_included():
    assert "frete não incluído" in format_message(_msg(shipping_included=False))
    assert "frete não incluído" in format_message(_msg(shipping_included=None))
    assert "frete não incluído" not in format_message(_msg(shipping_included=True))


def test_format_suspect_and_health_messages():
    suspect = format_message(_msg(kind="suspect"))
    assert "suspeito" in suspect.lower()
    assert "ALERTA MÁXIMO" not in suspect
    down = format_message(Message(kind="health", detail="zoom|down"))
    assert "zoom" in down and "fora do ar" in down
    up = format_message(Message(kind="health", detail="zoom|up"))
    assert "voltou" in up


def test_format_combo_offer_shows_combo_line_with_title():
    offer = make_offer(price="3500", bundle=True, title="PS5 Slim Digital – Pacote ASTRO BOT e Gran Turismo 7")
    text = format_message(Message(kind="max", model=offer.model, offer=offer))
    assert "🎮 Combo com jogos: PS5 Slim Digital – Pacote ASTRO BOT e Gran Turismo 7" in text


def test_format_plain_offer_has_no_combo_line():
    assert "Combo" not in format_message(_msg())


def test_format_message_includes_coupon_note():
    coupon = Coupon(store="kabum", code="BF10", description="10% off", source_url="https://c", seen_at=T0)
    text = format_message(_msg(), coupons=[coupon])
    assert "Cupom ativo: BF10" in text
    assert "Confira as condições" in text
