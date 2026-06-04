"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    anthropic_api_key: str
    callmebot_phone: str
    callmebot_api_key: str
    sheet_id: str
    plz: str
    supermarkets: tuple[str, ...] = ("Edeka", "Netto", "Kaufland")
    credentials_path: str = "credentials.json"

    @classmethod
    def from_env(cls) -> "Config":
        """Load and validate config from environment variables."""
        required = {
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "CALLMEBOT_PHONE": os.getenv("CALLMEBOT_PHONE"),
            "CALLMEBOT_APIKEY": os.getenv("CALLMEBOT_APIKEY"),
            "SHEET_ID": os.getenv("SHEET_ID"),
        }

        missing = [key for key, val in required.items() if not val]
        if missing:
            raise OSError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            anthropic_api_key=required["ANTHROPIC_API_KEY"],  # type: ignore[arg-type]
            callmebot_phone=required["CALLMEBOT_PHONE"],  # type: ignore[arg-type]
            callmebot_api_key=required["CALLMEBOT_APIKEY"],  # type: ignore[arg-type]
            sheet_id=required["SHEET_ID"],  # type: ignore[arg-type]
            plz=os.getenv("PLZ", "52428"),
        )
