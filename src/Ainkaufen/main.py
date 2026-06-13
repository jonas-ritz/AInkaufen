"""Entry point for the weekly grocery price optimizer."""

import logging
import sys

from .comparator import build_carts, rank_by_savings
from .config import Config
from .notifier import format_message, send_telegram
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
    ranked = rank_by_savings(shopping_carts)

    logger.info("Building carts for %d pantry items", len(pantry_items))
    pantry_carts = rank_by_savings(build_carts(pantry_items, config))

    # Print summary to terminal
    print("\n" + "=" * 60)
    print("WEEKLY GROCERY PRICE COMPARISON")
    print("Ranking: Supermarkt mit den höchsten Ersparnissen zuerst")
    print("(Summe aller Rabatte: Regelpreis minus Angebotspreis)")
    print("=" * 60)

    for i, cart in enumerate(ranked):
        medals = ["🥇", "🥈", "🥉", "4️⃣"]
        medal = medals[i] if i < len(medals) else "•"
        print(f"\n{medal} {cart.supermarket.upper()}")
        print(f"   Items found:  {len(cart.items)}")
        print(f"   Total price:  {cart.total_offer_price:.2f}€")
        print(f"   Total savings: {cart.total_savings:.2f}€")
        print("-" * 40)
        for offer in cart.items:
            savings_str = f"  save {offer.savings:.2f}€" if offer.savings else ""
            regular_str = f"was {offer.regular_price:.2f}€  " if offer.regular_price else ""
            print(f"   🏷️  {offer.description:<30} {offer.offer_price:.2f}€  {regular_str}{savings_str}")

    # Send WhatsApp notification
    message = format_message(ranked, pantry_carts)
    logger.info("Sending Telegram notification")
    send_telegram(message, config)


if __name__ == "__main__":
    main()