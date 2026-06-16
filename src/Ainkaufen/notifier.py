"""Email notification via SMTP."""

import logging
import smtplib
from email.message import EmailMessage

from .config import Config
from .models import CartSummary, PriceOffer

logger = logging.getLogger(__name__)

_MEDALS = ["🥇", "🥈", "🥉", "4️⃣"]


def format_message(
    ranked_carts: list[CartSummary],
    pantry_carts: list[CartSummary],
) -> str:
    lines: list[str] = [
        "🛒 <b>WEEKLY PRICE COMPARISON</b>",
        "<i>Ranking nach höchster Gesamtersparnis (Regelpreis - Angebotspreis)</i><br><br>",
    ]

    for i, cart in enumerate(ranked_carts):
        medal = _MEDALS[i] if i < len(_MEDALS) else "•"
        lines.append(f"{medal} <b>{cart.supermarket}</b><br>")
        lines.append(f"&nbsp;&nbsp;&nbsp;Angebote gefunden: {len(cart.items)}<br>")
        lines.append(f"&nbsp;&nbsp;&nbsp;Gesamtpreis: {cart.total_offer_price:.2f}€<br>")

        if cart.total_savings > 0:
            lines.append(
                f"&nbsp;&nbsp;&nbsp;💰 Ersparnis: {cart.total_savings:.2f}€ "
                f"({cart.items_with_savings} Artikel mit bekanntem Regelpreis)<br>"
            )
        lines.append("<br>")

    if ranked_carts:
        best = ranked_carts[0]
        lines.append(f"✅ <b>Empfehlung: {best.supermarket}</b><br>")
        if best.total_savings > 0:
            lines.append(f"&nbsp;&nbsp;&nbsp;Diese Woche {best.total_savings:.2f}€ sparen!<br>")

    pantry_offers: list[tuple[str, list[PriceOffer]]] = [
        (cart.supermarket, cart.items)
        for cart in pantry_carts
        if cart.items
    ]

    if pantry_offers:
        lines.append("<br>📦 <b>VORRATS-DEALS (diese Woche im Angebot)</b><br>")
        seen: set[str] = set()
        all_pantry = [
            (item, market)
            for market, items in pantry_offers
            for item in items
        ]
        for offer, market in sorted(all_pantry, key=lambda x: x[0].offer_price):
            if offer.description not in seen:
                seen.add(offer.description)
                savings_str = f" (spare {offer.savings:.2f}€)" if offer.savings else ""
                lines.append(
                    f"&nbsp;&nbsp;&nbsp;🏷️ {offer.description}: "
                    f"{offer.offer_price:.2f}€ @ {market}{savings_str}<br>"
                )

    return "\n".join(lines)


def send_email(message: str, config: Config) -> bool:
    email = EmailMessage()
    email["Subject"] = "🛒 Wöchentlicher Preisvergleich"
    email["From"] = config.smtp_user
    email["To"] = config.email_to
    email.set_content("Bitte HTML-fähigen E-Mail-Client verwenden.")
    email.add_alternative(f"<html><body>{message}</body></html>", subtype="html")

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
