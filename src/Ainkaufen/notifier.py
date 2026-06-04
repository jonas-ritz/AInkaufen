"""WhatsApp notification via CallMeBot."""

import logging
from urllib.parse import quote

import requests

from .config import Config
from .models import CartSummary, PriceOffer

logger = logging.getLogger(__name__)

_CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"
_MEDALS = ["🥇", "🥈", "🥉", "4️⃣"]


def format_message(
    ranked_carts: list[CartSummary],
    pantry_carts: dict[str, CartSummary],
) -> str:
    """
    Format the weekly WhatsApp summary message.

    Args:
        ranked_carts: Supermarket carts ranked by savings.
        pantry_carts: Carts for pantry/stockup items.

    Returns:
        Formatted message string ready to send.
    """
    lines: list[str] = ["🛒 *WEEKLY PRICE COMPARISON*\n"]

    for i, cart in enumerate(ranked_carts):
        medal = _MEDALS[i] if i < len(_MEDALS) else "•"
        lines.append(f"{medal} *{cart.supermarket}*")
        lines.append(f"   Offers found: {len(cart.items)} items")
        lines.append(f"   Total: {cart.total_offer_price:.2f}€")

        if cart.total_savings > 0:
            lines.append(
                f"   💰 Savings: {cart.total_savings:.2f}€ "
                f"({cart.items_with_savings} items with known regular price)"
            )
        lines.append("")

    if ranked_carts:
        best = ranked_carts[0]
        lines.append(f"✅ *Recommendation: {best.supermarket}*")
        if best.total_savings > 0:
            lines.append(f"   Save {best.total_savings:.2f}€ this week!")

    # Pantry tips
    pantry_offers: list[tuple[str, list[PriceOffer]]] = [
        (market, cart.items)
        for market, cart in pantry_carts.items()
        if cart.items
    ]

    if pantry_offers:
        lines.append("\n📦 *PANTRY DEALS (on sale this week)*")
        seen: set[str] = set()
        all_pantry = [
            (item, market)
            for market, items in pantry_offers
            for item in items
        ]
        for offer, market in sorted(all_pantry, key=lambda x: x[0].offer_price):
            if offer.description not in seen:
                seen.add(offer.description)
                savings_str = f" (save {offer.savings:.2f}€)" if offer.savings else ""
                lines.append(
                    f"   🏷️ {offer.description}: "
                    f"{offer.offer_price:.2f}€ @ {market}{savings_str}"
                )

    return "\n".join(lines)


def send_whatsapp(message: str, config: Config) -> bool:
    """
    Send a WhatsApp message via CallMeBot.

    Args:
        message: The message text to send.
        config: Application configuration with phone and API key.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    try:
        response = requests.get(
            _CALLMEBOT_URL,
            params={
                "phone": config.callmebot_phone,
                "text": quote(message),
                "apikey": config.callmebot_api_key,
            },
            timeout=15,
        )
        response.raise_for_status()
        logger.info("WhatsApp message sent successfully")
        return True
    except requests.RequestException as exc:
        logger.error("Failed to send WhatsApp message: %s", exc)
        return False