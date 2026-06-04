# AInkaufen

A weekly grocery price optimizer that tells you which supermarket saves you the most money.

I built this as a side project to learn more about API integration and AI-powered workflows — using Claude as a pair programmer throughout the whole thing.

---

## What it does

- Reads your grocery list from Google Sheets (checkboxes for what you need this week)
- Scrapes current offers from local supermarkets via Marktguru
- Uses Claude to match your items to the right offers (so "milk" doesn't match "chocolate milk")
- Ranks supermarkets by total savings
- Sends you a WhatsApp summary every Monday morning

---

## Stack

- Python 3.11
- Anthropic Claude API — for semantic product matching
- Google Sheets API — grocery list input
- Marktguru API — supermarket offer data
- Telegram / CallMeBot — weekly notifications
- `ruff` + `mypy` — linting and type checking

---

## Setup

```bash
git clone https://github.com/yourusername/ainkaufen.git
cd ainkaufen
python -m venv venv
venv\Scripts\activate
pip install -e .
```

Copy `.env.example` to `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...
SHEET_ID=your-google-sheet-id
CALLMEBOT_PHONE=+49...
CALLMEBOT_APIKEY=...
PLZ=52428
```

Also place your Google Service Account `credentials.json` in the project root and share your Sheet with the service account email.

---

## Google Sheet format

| Artikel | Kaufen | Kategorie |
|---|---|---|
| Milch | ✅ | Frisch |
| Nudeln | ☐ | Vorrat |

Checkboxes via Insert → Checkbox. Category is either `Frisch` or `Vorrat`.

---

## Run

```bash
python -m Ainkaufen.main
```

```bash
ruff check src/
mypy src/
pytest tests/ -v
```

---

## Automate with GitHub Actions

```yaml
name: Weekly Price Check
on:
  schedule:
    - cron: '0 8 * * 1'
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e .
      - run: python -m Ainkaufen.main
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          SHEET_ID: ${{ secrets.SHEET_ID }}
          CALLMEBOT_PHONE: ${{ secrets.CALLMEBOT_PHONE }}
          CALLMEBOT_APIKEY: ${{ secrets.CALLMEBOT_APIKEY }}
          PLZ: 52428
```

---

## About

Built as a learning project with Claude (Anthropic) as an AI pair programmer. The goal was to get hands-on experience with real APIs, clean Python architecture, and using LLMs as functional components in a pipeline — not just for chat.
