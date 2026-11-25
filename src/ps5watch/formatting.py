from __future__ import annotations

from decimal import Decimal

from ps5watch.alerts import Message
from ps5watch.models import Coupon, ModelKey

MODEL_NAMES = {
    ModelKey.SLIM_DISC: "PS5 Slim com leitor de disco",
    ModelKey.SLIM_DIGITAL: "PS5 Slim Digital",
}


def brl(value: Decimal) -> str:
    cents = f"{value:,.2f}"  # 3,499.00
    return "R$ " + cents.replace(",", "X").replace(".", ",").replace("X", ".")


def _health_text(detail: str) -> str:
    name, status, pages_text = (detail.split("|") + ["", ""])[:3]
    pages = [p for p in pages_text.split(", ") if p]
    if pages:
        count = f"{len(pages)} página" if len(pages) == 1 else f"{len(pages)} páginas"
        listing = "\n".join(f"• {p}" for p in pages)
        if status == "up":
            return f"✅ {name}: {count} voltou a funcionar:\n{listing}"
        return (
            f"⚠️ {name}: {count} fora do ar há mais de 10 minutos:\n{listing}\n"
            "As ofertas dessas páginas não estão sendo conferidas."
        )
    if status == "up":
        return f"✅ A fonte {name} voltou a funcionar."
    return (
        f"⚠️ A fonte {name} está fora do ar há mais de 10 minutos. "
        "Os preços dela não estão sendo conferidos."
    )


def format_message(msg: Message, coupons: list[Coupon] | None = None) -> str:
    if msg.kind == "health":
        return _health_text(msg.detail)

    offer = msg.offer
    model = MODEL_NAMES[msg.model]
    if msg.kind == "max":
        header = "🚨🚨 ALERTA MÁXIMO 🚨🚨"
    elif msg.kind == "suspect":
        header = "❓ Preço suspeito, confira se é o console mesmo"
    else:
        header = "🔔 Preço abaixo de R$ 4.000"

    lines = [header, f"{model} — {offer.store}"]
    if offer.bundle:
        lines.append(f"🎮 Combo com jogos: {offer.title}" if offer.title else "🎮 Combo com jogos")
    lines.append(f"À vista/Pix: {brl(offer.price_cash)}")
    if offer.price_installment is not None:
        lines.append(f"Parcelado: {brl(offer.price_installment)}")
    if msg.low_30d is None:
        lines.append("📉 menor preço dos últimos 30 dias: sem histórico ainda")
    else:
        lines.append(f"📉 menor preço dos últimos 30 dias: {brl(msg.low_30d)}")
    if offer.shipping_included is not True:
        lines.append("(frete não incluído)")

    for coupon in coupons or []:
        if coupon.store.lower() == offer.store.lower():
            lines.append(f"Cupom ativo: {coupon.code} — {coupon.description}. Confira as condições.")

    lines.append(offer.url)
    return "\n".join(lines)
