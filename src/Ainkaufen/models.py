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
    regular_price: float | None = None

    @property
    def savings(self) -> float | None:
        """Return savings compared to regular price, if known."""
        if self.regular_price is None:
            return None
        return max(self.regular_price - self.offer_price, 0.0)


@dataclass
class CartSummary:
    """Summary of found offers for one supermarket."""

    supermarket: str
    items: list[PriceOffer] = field(default_factory=list)

    @property
    def total_offer_price(self) -> float:
        return sum(item.offer_price for item in self.items)

    @property
    def total_savings(self) -> float:
        return sum(item.savings for item in self.items if item.savings is not None)

    @property
    def items_with_savings(self) -> int:
        return sum(1 for item in self.items if item.savings is not None)