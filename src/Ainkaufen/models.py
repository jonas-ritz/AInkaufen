"""Domain models for the grocery price optimizer."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GroceryItem:
    """A single item from the shopping list."""

    name: str
    category: str
    should_buy: bool


@dataclass(frozen=True)
class PriceOffer:
    """A price offer from a supermarket for a specific product."""

    supermarket: str
    description: str
    offer_price: float


@dataclass
class CartSummary:
    """Summary of found offers for one supermarket."""

    supermarket: str
    items: list[PriceOffer] = field(default_factory=list)

    @property
    def total_offer_price(self) -> float:
        return sum(item.offer_price for item in self.items)