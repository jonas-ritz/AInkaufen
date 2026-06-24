"""Email notification via SMTP."""

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from .models import CartSummary

logger = logging.getLogger(__name__)

_MEDALS = ["🥇", "🥈", "🥉", "4️⃣"]


class _SMTPConfig(Protocol):
    """Structural interface satisfied by both Config and DigestConfig."""

    smtp_user: str
    smtp_password: str
    smtp_host: str
    smtp_port: int
    email_to: str


def _offer_line_html(offer: object) -> str:
    """Render one PriceOffer as an HTML line."""
    return (
        f"&nbsp;&nbsp;&nbsp;&nbsp;🏷️ {offer.description}"  # type: ignore[attr-defined]
        f"&nbsp;&nbsp;{offer.offer_price:.2f}€<br>"  # type: ignore[attr-defined]
    )


def _all_markets_ordered(
    ranked_carts: list[CartSummary],
    pantry_by_market: dict[str, CartSummary],
) -> list[tuple[int, CartSummary]]:
    """Return (medal_index, shopping_cart) for every market, ranked first."""
    seen: set[str] = set()
    result: list[tuple[int, CartSummary]] = []
    for i, cart in enumerate(ranked_carts):
        result.append((i, cart))
        seen.add(cart.supermarket)
    # markets that only have pantry deals (no shopping items)
    for cart in pantry_by_market.values():
        if cart.supermarket not in seen:
            result.append((len(result), CartSummary(supermarket=cart.supermarket)))
    return result


def format_message(
    ranked_carts: list[CartSummary],
    pantry_carts: list[CartSummary],
) -> str:
    pantry_by_market = {cart.supermarket: cart for cart in pantry_carts}
    markets = _all_markets_ordered(ranked_carts, pantry_by_market)

    lines: list[str] = [
        "🛒 <b>TÄGLICHER PREISVERGLEICH</b>",
        "<i>Ranking nach höchstem Angebotsvolumen</i><br><br>",
    ]

    for i, cart in markets:
        medal = _MEDALS[i] if i < len(_MEDALS) else "•"
        pantry = pantry_by_market.get(cart.supermarket)

        shopping_price = cart.total_offer_price
        pantry_price = pantry.total_offer_price if pantry else 0.0
        total_price = shopping_price + pantry_price

        lines.append(f"{medal} <b>{cart.supermarket.upper()}</b><br>")
        lines.append(
            f"&nbsp;&nbsp;&nbsp;💰 Gesamt: <b>{total_price:.2f}€</b>"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;🛍️ Einkauf: {shopping_price:.2f}€"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;📦 Vorrat: {pantry_price:.2f}€<br>"
        )

        if cart.items:
            lines.append("&nbsp;&nbsp;&nbsp;🛍️ <u>Wocheneinkauf</u><br>")
            for offer in cart.items:
                lines.append(_offer_line_html(offer))
        else:
            lines.append("&nbsp;&nbsp;&nbsp;<i>Keine passenden Angebote diese Woche.</i><br>")

        if pantry and pantry.items:
            lines.append("&nbsp;&nbsp;&nbsp;📦 <u>Vorrat</u><br>")
            for offer in pantry.items:
                lines.append(_offer_line_html(offer))

        lines.append("<br>")

    if ranked_carts:
        best = ranked_carts[0]
        best_pantry = pantry_by_market.get(best.supermarket)
        total_best_price = best.total_offer_price + (best_pantry.total_offer_price if best_pantry else 0)
        note = f"&nbsp;— höchstes Angebotsvolumen ({total_best_price:.2f}€)" if total_best_price > 0 else ""
        lines.append(f"✅ <b>Empfehlung: {best.supermarket}</b>{note}<br>")

    return "\n".join(lines)


def send_email(
    message: str,
    config: _SMTPConfig,
    subject: str = "🛒 Täglicher Preisvergleich",
) -> bool:
    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = config.smtp_user
    email["To"] = config.email_to
    html = (
        "<html><body style=\"font-family:sans-serif;max-width:640px;"
        "margin:0 auto;padding:24px;color:#1a1a1a;line-height:1.6\">"
        f"{message}"
        "</body></html>"
    )
    email.set_content("Bitte HTML-fähigen E-Mail-Client verwenden.")
    email.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=15) as server:
            server.starttls()
            server.login(config.smtp_user, config.smtp_password)
            server.send_message(email)
        logger.info("Email sent successfully to %s", config.email_to)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        logger.error("Failed to send email: %s", exc)
        return False
