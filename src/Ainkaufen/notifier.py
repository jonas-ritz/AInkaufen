"""Telegram notification via Bot API."""

import logging

import requests

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
        "<i>Ranking nach höchster Gesamtersparnis (Regelpreis - Angebotspreis)</i>\n",
    ]

    for i, cart in enumerate(ranked_carts):
        medal = _MEDALS[i] if i < len(_MEDALS) else "•"
        lines.append(f"{medal} <b>{cart.supermarket}</b>")
        lines.append(f"   Angebote gefunden: {len(cart.items)}")
        lines.append(f"   Gesamtpreis: {cart.total_offer_price:.2f}€")

        if cart.total_savings > 0:
            lines.append(
                f"   💰 Ersparnis: {cart.total_savings:.2f}€ "
                f"({cart.items_with_savings} Artikel mit bekanntem Regelpreis)"
            )
        lines.append("")

    if ranked_carts:
        best = ranked_carts[0]
        lines.append(f"✅ <b>Empfehlung: {best.supermarket}</b>")
        if best.total_savings > 0:
            lines.append(f"   Diese Woche {best.total_savings:.2f}€ sparen!")

    pantry_offers: list[tuple[str, list[PriceOffer]]] = [
        (cart.supermarket, cart.items)
        for cart in pantry_carts
        if cart.items
    ]

    if pantry_offers:
        lines.append("\n📦 <b>VORRATS-DEALS (diese Woche im Angebot)</b>")
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
                    f"   🏷️ {offer.description}: "
                    f"{offer.offer_price:.2f}€ @ {market}{savings_str}"
                )

    return "\n".join(lines)


def send_telegram(message: str, config: Config) -> bool:
    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    try:
        response = requests.post(
            url,
            json={
                "chat_id": config.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
        response.raise_for_status()
        logger.info("Telegram message sent successfully")
        return True
    except requests.RequestException as exc:
        logger.error("Failed to send Telegram message: %s", exc)
        if hasattr(exc, "response") and exc.response is not None:
            logger.error("Telegram API error: %s", exc.response.text)
        return False
