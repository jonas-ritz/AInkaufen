"""Price comparison logic across supermarkets."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import Config
from .matcher import match_best_offers
from .models import CartSummary, GroceryItem, PriceOffer
from .scraper import fetch_offers

logger = logging.getLogger(__name__)


def _fetch_and_match(item: GroceryItem, config: Config) -> dict[str, PriceOffer | None]:
    logger.info("Searching offers for: %s", item.name)
    offers = fetch_offers(item.name, config)
    return match_best_offers(item.name, offers, config)


def build_carts(
    items: list[GroceryItem],
    config: Config,
) -> dict[str, CartSummary]:
    """
    Build a CartSummary per supermarket for a list of grocery items.
    Items are fetched and matched concurrently; results are merged sequentially.
    """
    carts: dict[str, CartSummary] = {
        market: CartSummary(supermarket=market) for market in config.supermarkets
    }

    with ThreadPoolExecutor(max_workers=min(len(items), 8)) as executor:
        futures = {executor.submit(_fetch_and_match, item, config): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            try:
                best_per_market = future.result()
            except Exception as exc:
                logger.warning("Failed to process '%s': %s", item.name, exc)
                continue
            for market, offer in best_per_market.items():
                if offer is not None:
                    carts[market].items.append(offer)

    return carts


def rank_by_offer_volume(carts: dict[str, CartSummary]) -> list[CartSummary]:
    """
    Rank supermarkets by total offer volume (sum of offer prices) descending.

    The assumption is a uniform discount rate across all products: a higher total
    offer price means higher absolute savings, regardless of which regular prices
    the supermarket would otherwise charge.  Markets with no matching offers are excluded.
    """
    active = [c for c in carts.values() if c.items]
    return sorted(active, key=lambda c: c.total_offer_price, reverse=True)
