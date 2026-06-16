"""Tests for the Claude-powered offer matcher."""

import json
from unittest.mock import MagicMock, patch

import pytest

from Ainkaufen.config import Config
from Ainkaufen.matcher import match_best_offers
from Ainkaufen.models import PriceOffer


@pytest.fixture
def config() -> Config:
    return Config(
        anthropic_api_key="test-key",
        smtp_user="test@example.com",
        smtp_password="abc",
        sheet_id="sheet-id",
        plz="12345",
        email_to="test@example.com",
        supermarkets=("Edeka", "Netto", "Kaufland"),
    )


@pytest.fixture
def offers() -> list[PriceOffer]:
    return [
        PriceOffer(supermarket="Edeka", description="Whole milk 1L", offer_price=0.99, regular_price=1.29),
        PriceOffer(supermarket="Netto", description="Fresh milk 1L", offer_price=1.09, regular_price=None),
        PriceOffer(supermarket="Kaufland", description="Butter 250g", offer_price=1.49, regular_price=1.89),
    ]


def _make_response(payload: dict) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(payload))]
    return msg


@patch("Ainkaufen.matcher.anthropic.Anthropic")
class TestMatchBestOffers:
    def test_returns_original_offer_objects_by_index(self, mock_cls, config, offers):
        mock_cls.return_value.messages.create.return_value = _make_response(
            {"Edeka": {"index": 1}, "Netto": {"index": 2}, "Kaufland": None}
        )

        result = match_best_offers("milk", offers, config)

        assert result["Edeka"] is offers[0]
        assert result["Netto"] is offers[1]
        assert result["Kaufland"] is None

    def test_ignores_prices_returned_by_claude(self, mock_cls, config, offers):
        # Claude returning wrong prices must not affect the result
        mock_cls.return_value.messages.create.return_value = _make_response(
            {"Edeka": {"index": 1, "offer_price": 9999.99}, "Netto": None, "Kaufland": None}
        )

        result = match_best_offers("milk", offers, config)

        assert result["Edeka"] is offers[0]
        assert result["Edeka"].offer_price == 0.99

    def test_empty_offers_skips_api_call(self, mock_cls, config):
        result = match_best_offers("milk", [], config)

        mock_cls.assert_not_called()
        assert result == {"Edeka": None, "Netto": None, "Kaufland": None}

    def test_api_error_returns_all_none(self, mock_cls, config, offers):
        import anthropic as _anthropic

        class _StubError(_anthropic.APIError):
            def __init__(self) -> None:
                pass

        mock_cls.return_value.messages.create.side_effect = _StubError()

        result = match_best_offers("milk", offers, config)

        assert result == {"Edeka": None, "Netto": None, "Kaufland": None}

    def test_invalid_json_returns_all_none(self, mock_cls, config, offers):
        msg = MagicMock()
        msg.content = [MagicMock(text="not valid json")]
        mock_cls.return_value.messages.create.return_value = msg

        result = match_best_offers("milk", offers, config)

        assert result == {"Edeka": None, "Netto": None, "Kaufland": None}

    def test_fenced_json_response_is_parsed(self, mock_cls, config, offers):
        raw = "```json\n" + json.dumps({"Edeka": {"index": 1}, "Netto": None, "Kaufland": None}) + "\n```"
        msg = MagicMock()
        msg.content = [MagicMock(text=raw)]
        mock_cls.return_value.messages.create.return_value = msg

        result = match_best_offers("milk", offers, config)

        assert result["Edeka"] is offers[0]

    def test_out_of_range_index_returns_none_for_that_market(self, mock_cls, config, offers):
        mock_cls.return_value.messages.create.return_value = _make_response(
            {"Edeka": {"index": 99}, "Netto": None, "Kaufland": None}
        )

        result = match_best_offers("milk", offers, config)

        assert result["Edeka"] is None

    def test_zero_index_returns_none_for_that_market(self, mock_cls, config, offers):
        mock_cls.return_value.messages.create.return_value = _make_response(
            {"Edeka": {"index": 0}, "Netto": None, "Kaufland": None}
        )

        result = match_best_offers("milk", offers, config)

        assert result["Edeka"] is None

    def test_missing_market_in_response_returns_none(self, mock_cls, config, offers):
        # Claude omits a market entirely
        mock_cls.return_value.messages.create.return_value = _make_response(
            {"Edeka": {"index": 1}}
        )

        result = match_best_offers("milk", offers, config)

        assert result["Edeka"] is offers[0]
        assert result["Netto"] is None
        assert result["Kaufland"] is None

    def test_example_json_in_prompt_uses_actual_supermarkets(self, mock_cls, config, offers):
        mock_cls.return_value.messages.create.return_value = _make_response(
            {"Edeka": None, "Netto": None, "Kaufland": None}
        )

        match_best_offers("milk", offers, config)

        call_args = mock_cls.return_value.messages.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        # The example JSON must contain all three configured supermarkets
        for market in config.supermarkets:
            assert market in prompt
