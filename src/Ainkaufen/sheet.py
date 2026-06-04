"""Google Sheets client for reading the grocery list."""

import logging

import gspread
from google.oauth2.service_account import Credentials

from .config import Config
from .models import GroceryItem

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def load_grocery_list(config: Config) -> tuple[list[GroceryItem], list[GroceryItem]]:
    """
    Load grocery items from Google Sheets.

    Returns:
        A tuple of (items_to_buy, pantry_items) where pantry_items
        are unchecked items in the 'Vorrat' category worth buying on sale.
    """
    creds = Credentials.from_service_account_file(
        config.credentials_path, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(config.sheet_id).sheet1
    rows = sheet.get_all_records()

    logger.info("Loaded %d rows from Google Sheets", len(rows))

    items_to_buy: list[GroceryItem] = []
    pantry_items: list[GroceryItem] = []

    for row in rows:
        name = str(row.get("Artikel", "")).strip()
        category = str(row.get("Kategorie", "")).strip()
        checked = str(row.get("Kaufen", "")).upper() == "TRUE"

        if not name:
            continue

        item = GroceryItem(name=name, category=category, should_buy=checked)

        if checked:
            items_to_buy.append(item)
        elif category == "Vorrat":
            pantry_items.append(item)

    logger.info(
        "Found %d items to buy, %d pantry candidates",
        len(items_to_buy),
        len(pantry_items),
    )
    return items_to_buy, pantry_items