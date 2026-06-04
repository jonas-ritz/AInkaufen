"""Claude AI-powered offer matching to find the best offer per supermarket."""

import json
import logging

import anthropic

from .config import Config
from .models import PriceOffer

logger = logging.getLogger(__name__)


def match_best_offers(
    item_name: str,
    offers: list[PriceOffer],
    config: Config,
) -> dict[str, PriceOffer | None]:
    """
    Use Claude to find the best semantically matching offer per supermarket.

    Args:
        item_name: The item the user is looking for.
        offers: Raw list of offers returned by the scraper.
        config: Application configuration.

    Returns:
        A dict mapping supermarket name to its best matching PriceOffer,
        or None if no suitable offer was found.
    """
    if not offers:
        return {market: None for market in config.supermarkets}

    offers_text = "\n".join(
        f"{i + 1}. {o.supermarket}: {o.offer_price:.2f}€"
        + (f" (regular: {o.regular_price:.2f}€)" if o.regular_price else "")
        + f" — {o.description}"
        for i, o in enumerate(offers)
    )

    prompt = f"""The user is looking for: "{item_name}"

Available offers this week:
{offers_text}

Supermarkets: {", ".join(config.supermarkets)}

Task:
- For each supermarket, select the offer that best semantically matches "{item_name}".
- Ignore clearly unrelated products (e.g. "chocolate milk" when searching for "milk").
- If no suitable offer exists for a supermarket, return null.
- Do not invent prices.

Respond with JSON only, no preamble:
{{
    "Edeka": {{"index": 1, "offer_price": 0.99, "regular_price": 1.29, "description": "Whole milk 1L"}},
    "Netto": null,
    "Kaufland": {{"index": 3, "offer_price": 1.09, "regular_price": null, "description": "Fresh milk 1L"}}
}}"""

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip().replace("```json", "").replace("```", "")
        matches: dict[str, dict | None] = json.loads(text)
    except (anthropic.APIError, json.JSONDecodeError) as exc:
        logger.warning("Matching failed for '%s': %s", item_name, exc)
        return {market: None for market in config.supermarkets}

    result: dict[str, PriceOffer | None] = {}
    for market in config.supermarkets:
        match = matches.get(market)
        if match is None:
            result[market] = None
            continue

        result[market] = PriceOffer(
            supermarket=market,
            description=match["description"],
            offer_price=float(match["offer_price"]),
            regular_price=float(match["regular_price"]) if match.get("regular_price") else None,
        )

    return result