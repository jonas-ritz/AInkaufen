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

    Returns the original PriceOffer from the scraped list (via index),
    so prices are always authoritative and never hallucinated by the model.
    """
    if not offers:
        return {market: None for market in config.supermarkets}

    offers_text = "\n".join(
        f"{i + 1}. {o.supermarket}: {o.offer_price:.2f}€"
        + (f" (regular: {o.regular_price:.2f}€)" if o.regular_price else "")
        + f" — {o.description}"
        for i, o in enumerate(offers)
    )

    # Build example JSON dynamically so it always reflects the actual supermarket list
    example_markets = {config.supermarkets[0]: {"index": 1}}
    example_markets.update({m: None for m in config.supermarkets[1:]})
    example_json = json.dumps(example_markets, ensure_ascii=False)

    prompt = f"""The user is looking for: "{item_name}"

Available offers this week:
{offers_text}

Supermarkets: {", ".join(config.supermarkets)}

Task:
- For each supermarket, return the offer NUMBER (index) that best semantically matches "{item_name}".
- Ignore clearly unrelated products (e.g. "chocolate milk" when searching for "milk").
- If no suitable offer exists for a supermarket, return null.

Respond with JSON only, no preamble:
{example_json}"""

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Strip optional fenced code block
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
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

        idx = match.get("index")
        if not isinstance(idx, int) or not (1 <= idx <= len(offers)):
            logger.warning("Invalid index %r from Claude for '%s' @ %s", idx, item_name, market)
            result[market] = None
            continue

        result[market] = offers[idx - 1]

    return result
