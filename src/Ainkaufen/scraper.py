"""Marktguru API client for fetching supermarket offers."""

import logging

import requests

from .config import Config
from .models import PriceOffer

logger = logging.getLogger(__name__)

_MARKTGURU_URL = "https://api.marktguru.de/api/v1/offers/search"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "x-clientkey": "WU/RH+PMGDi+gkZer3WbMelt6zcYHSTytNB7VpTia90=",
    "x-apikey": "8Kk+pmbf7TgJ9nVj2cXeA7P5zBGv8iuutVVMRfOfvNE=",
}


def fetch_offers(item_name: str, config: Config) -> list[PriceOffer]:
    """
    Fetch current supermarket offers for a given item from Marktguru.

    Args:
        item_name: The grocery item to search for.
        config: Application configuration containing PLZ and supermarket list.

    Returns:
        A list of PriceOffer objects from matching supermarkets.
    """
    params = {
        "as": "web",
        "limit": 24,
        "offset": 0,
        "q": item_name,
        "zipCode": config.plz,
    }

    try:
        response = requests.get(
            _MARKTGURU_URL, headers=_HEADERS, params=params, timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("Marktguru request failed for '%s': %s", item_name, exc)
        return []

    offers: list[PriceOffer] = []

    for result in data.get("results", []):
        advertisers = [a.get("name", "") for a in result.get("advertisers", [])]
        matched_markets = [
            a
            for a in advertisers
            if any(s.lower() in a.lower() for s in config.supermarkets)
        ]

        if not matched_markets:
            continue

        offer_price = result.get("price")
        if offer_price is None:
            continue

        regular_price = result.get("regularPrice")
        description = result.get("description", item_name)

        for market in matched_markets:
            offers.append(
                PriceOffer(
                    supermarket=market,
                    description=description,
                    offer_price=float(offer_price),
                    regular_price=float(regular_price) if regular_price else None,
                )
            )

    logger.debug("Found %d offers for '%s'", len(offers), item_name)
    return offers