"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    anthropic_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    sheet_id: str
    plz: str
    supermarkets: tuple[str, ...] = ("Edeka", "Netto", "Kaufland")
    credentials_path: str = "credentials.json"

    @classmethod
    def from_env(cls) -> "Config":
        """Load and validate config from environment variables."""
        required = {
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
            "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
            "SHEET_ID": os.getenv("SHEET_ID"),
        }

        missing = [key for key, val in required.items() if not val]
        if missing:
            raise OSError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            anthropic_api_key=required["ANTHROPIC_API_KEY"],  # type: ignore[arg-type]
            telegram_bot_token=required["TELEGRAM_BOT_TOKEN"],  # type: ignore[arg-type]
            telegram_chat_id=required["TELEGRAM_CHAT_ID"],  # type: ignore[arg-type]
            sheet_id=required["SHEET_ID"],  # type: ignore[arg-type]
            plz=os.getenv("PLZ", "52428"),
        )
