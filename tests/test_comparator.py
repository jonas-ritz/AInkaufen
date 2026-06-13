"""Unit tests for the price comparison logic."""

from Ainkaufen.models import CartSummary, PriceOffer


def test_cart_summary_total_savings() -> None:
    cart = CartSummary(
        supermarket="Rewe",
        items=[
            PriceOffer("Rewe", "Milk 1L", 0.99, regular_price=1.29),
            PriceOffer("Rewe", "Bread 500g", 1.49, regular_price=None),
            PriceOffer("Rewe", "Butter 250g", 1.79, regular_price=2.19),
        ],
    )
    assert cart.total_savings == 0.70
    assert cart.items_with_savings == 2
    assert cart.total_offer_price == 4.27


def test_cart_summary_no_savings() -> None:
    cart = CartSummary(
        supermarket="Aldi",
        items=[PriceOffer("Aldi", "Eggs 10x", 1.99, regular_price=None)],
    )
    assert cart.total_savings == 0.0
    assert cart.items_with_savings == 0


def test_price_offer_savings_property() -> None:
    import pytest

    offer = PriceOffer("Edeka", "Yogurt", 0.49, regular_price=0.79)
    assert offer.savings == pytest.approx(0.30)

    offer_no_regular = PriceOffer("Edeka", "Yogurt", 0.49, regular_price=None)
    assert offer_no_regular.savings is None