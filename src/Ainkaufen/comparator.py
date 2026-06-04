"""Price comparison logic across supermarkets."""

import logging

from .config import Config
from .models import CartSummary, GroceryItem, PriceOffer
from .matcher import match_best_offers
from .scraper import fetch_offers

logger = logging.getLogger(__name__)


def build_carts(
    items: list[GroceryItem],
    config: Config,
) -> dict[str, CartSummary]:
    """
    Build a CartSummary per supermarket for a list of grocery items.

    Args:
        items: List of grocery items to look up.
        config: Application configuration.

    Returns:
        A dict mapping supermarket name to its CartSummary.
    """
    carts: dict[str, CartSummary] = {
        market: CartSummary(supermarket=market) for market in config.supermarkets
    }

    for item in items:
        logger.info("Searching offers for: %s", item.name)
        offers = fetch_offers(item.name, config)
        best_per_market = match_best_offers(item.name, offers, config)

        for market, offer in best_per_market.items():
            if offer is not None:
                carts[market].items.append(offer)

    return carts


def rank_by_savings(carts: dict[str, CartSummary]) -> list[CartSummary]:
    """
    Rank supermarkets by total savings descending.

    Args:
        carts: Dict of CartSummary objects per supermarket.

    Returns:
        Sorted list of CartSummary, highest savings first.
    """
    return sorted(carts.values(), key=lambda c: c.total_savings, reverse=True)