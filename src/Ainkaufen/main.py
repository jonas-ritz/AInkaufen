"""Entry point for the weekly grocery price optimizer."""

import logging
import sys

from .comparator import build_carts, rank_by_offer_volume
from .config import Config
from .notifier import format_message, send_email
from .sheet import load_grocery_list

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the weekly grocery price comparison."""
    logger.info("Starting grocery price optimizer")

    try:
        config = Config.from_env()
    except OSError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    # Load grocery list from Google Sheets
    items_to_buy, pantry_items = load_grocery_list(config)

    # Build price comparisons
    logger.info("Building carts for %d items to buy", len(items_to_buy))
    shopping_carts = build_carts(items_to_buy, config)
    ranked = rank_by_offer_volume(shopping_carts)

    logger.info("Building carts for %d pantry items", len(pantry_items))
    pantry_carts = rank_by_offer_volume(build_carts(pantry_items, config))

    # Print summary to terminal
    pantry_by_market = {cart.supermarket: cart for cart in pantry_carts}
    medals = ["🥇", "🥈", "🥉", "4️⃣"]

    print("\n" + "=" * 60)
    print("TÄGLICHER PREISVERGLEICH")
    print("Ranking: Supermarkt mit dem höchsten Angebotsvolumen zuerst")
    print("=" * 60)

    for i, cart in enumerate(ranked):
        medal = medals[i] if i < len(medals) else "•"
        pantry = pantry_by_market.get(cart.supermarket)
        shopping_price = cart.total_offer_price
        pantry_price = pantry.total_offer_price if pantry else 0.0
        total_price = shopping_price + pantry_price

        print(f"\n{medal} {cart.supermarket.upper()}")
        print(f"   💰 Gesamt: {total_price:.2f}€  |  🛍️ Einkauf: {shopping_price:.2f}€  |  📦 Vorrat: {pantry_price:.2f}€")
        print("-" * 40)

        if cart.items:
            print("   🛍️  Wocheneinkauf:")
            for offer in cart.items:
                print(f"      🏷️  {offer.description:<30} {offer.offer_price:.2f}€")
        else:
            print("   Keine passenden Angebote diese Woche.")

        if pantry and pantry.items:
            print("   📦  Vorrat:")
            for offer in pantry.items:
                print(f"      🏷️  {offer.description:<30} {offer.offer_price:.2f}€")

    # Send email notification
    message = format_message(ranked, pantry_carts)
    logger.info("Sending email notification to %s", config.email_to)
    if not send_email(message, config):
        logger.error("Email notification failed")
        sys.exit(1)


if __name__ == "__main__":
    main()