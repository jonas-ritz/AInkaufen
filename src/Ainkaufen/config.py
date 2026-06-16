"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    anthropic_api_key: str
    smtp_user: str
    smtp_password: str
    sheet_id: str
    plz: str
    email_to: str
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    supermarkets: tuple[str, ...] = ("Edeka", "Netto", "Kaufland")
    credentials_path: str = "credentials.json"

    @classmethod
    def from_env(cls) -> "Config":
        """Load and validate config from environment variables."""
        required = {
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "SMTP_USER": os.getenv("SMTP_USER"),
            "SMTP_PASSWORD": os.getenv("SMTP_PASSWORD"),
            "SHEET_ID": os.getenv("SHEET_ID"),
            "PLZ": os.getenv("PLZ"),
            "EMAIL_TO": os.getenv("EMAIL_TO"),
        }

        missing = [key for key, val in required.items() if not val]
        if missing:
            raise OSError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

        return cls(
            anthropic_api_key=required["ANTHROPIC_API_KEY"],  # type: ignore[arg-type]
            smtp_user=required["SMTP_USER"],  # type: ignore[arg-type]
            smtp_password=required["SMTP_PASSWORD"],  # type: ignore[arg-type]
            sheet_id=required["SHEET_ID"],  # type: ignore[arg-type]
            plz=required["PLZ"],  # type: ignore[arg-type]
            email_to=required["EMAIL_TO"],  # type: ignore[arg-type]
            smtp_host=os.getenv("SMTP_HOST") or "smtp.gmail.com",
            smtp_port=int(os.getenv("SMTP_PORT") or "587"),
        )
