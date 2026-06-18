# AInkaufen

A personal daily automation that does two things: tells you which supermarket saves you the most money this week, and sends you a curated AI news digest every morning.

Built as a side project to get hands-on experience with real APIs and AI-powered workflows — using Claude as a pair programmer throughout.

---

## Features

### 🛒 Daily Price Comparison
- Reads your grocery list from Google Sheets (checkboxes for what you need this week vs. what to stock up on)
- Scrapes current offers from local supermarkets via Marktguru
- Uses Claude to semantically match your items to the right offers — so "Milch" doesn't match "Schokoladenmilch"
- Ranks supermarkets by total savings, split into weekly shopping and pantry stock
- Sends a formatted HTML email with per-supermarket breakdowns

### 🤖 Daily AI Digest
- Fetches the latest AI news from the past 24 hours via Claude's built-in web search
- Summarises 3–5 relevant stories for software developers (software, society, business — not hardware specs)
- Includes a rotating "Concept of the Day" explaining one AI technique in depth with analogies and optionally math
- Sends a separate HTML email every morning

---

## Stack

| Component | Used for |
|---|---|
| Python 3.11 | Everything |
| [Anthropic Claude API](https://docs.anthropic.com) | Semantic product matching · AI digest with web search |
| Google Sheets API | Grocery list input |
| Marktguru API | Supermarket offer data |
| SMTP (`smtplib`) | Email delivery |
| GitHub Actions | Daily scheduling |
| `ruff` + `mypy` | Linting and type checking |

---

## Setup

```bash
git clone https://github.com/jonas-ritz/AInkaufen.git
cd AInkaufen
python -m venv venv
venv\Scripts\activate
pip install -e .
```

Create a `.env` file in the project root:

```env
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Email (sender account — needs Gmail App Password)
SMTP_USER=your-gmail@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_HOST=smtp.gmail.com   # optional, this is the default
SMTP_PORT=587               # optional, this is the default
EMAIL_TO=recipient@example.com

# Price comparison only
SHEET_ID=your-google-sheet-id
PLZ=12345
```

**Gmail App Password:** Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and create one. 2-Step Verification must be enabled first.

**Google credentials:** Place your Google Service Account `credentials.json` in the project root and share your Sheet with the service account email.

---

## Google Sheet format

| Artikel | Kaufen | Kategorie |
|---|---|---|
| Milch | ✅ | Frisch |
| Nudeln | ☐ | Vorrat |

- **Kaufen** — checkbox (Insert → Checkbox). Checked = buy this week.
- **Kategorie** — either `Frisch` (weekly shopping) or `Vorrat` (pantry stock).

---

## Run locally

**Price comparison:**
```bash
python -m Ainkaufen.main
```

**AI digest:**
```bash
python -m Ainkaufen.digest
```

**Tests & linting:**
```bash
pytest tests/ -v
ruff check src/
mypy src/
```

---

## Automate with GitHub Actions

Two independent workflows run daily — no overlap in secrets required:

| Workflow | Schedule | File |
|---|---|---|
| Price comparison | ~06:00 CET | [daily.yml](.github/workflows/daily.yml) |
| AI digest | ~07:30 CET | [daily-digest.yml](.github/workflows/daily-digest.yml) |

Both can be triggered manually via **Run workflow** in the Actions tab.

### Required secrets

Go to **Settings → Secrets and variables → Actions** and add:

**Shared by both workflows:**
| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `SMTP_USER` | Gmail address used to send emails |
| `SMTP_PASSWORD` | Gmail App Password |
| `EMAIL_TO` | Recipient email address |
| `SMTP_HOST` | Optional — defaults to `smtp.gmail.com` |
| `SMTP_PORT` | Optional — defaults to `587` |

**Price comparison only:**
| Secret | Description |
|---|---|
| `SHEET_ID` | Google Sheets document ID |
| `PLZ` | Your German postal code (for local offers) |
| `GOOGLE_CREDENTIALS` | Full contents of your `credentials.json` |

---

## Project structure

```
src/Ainkaufen/
├── config.py      # Config and DigestConfig dataclasses
├── digest.py      # AI digest: Claude web search → email
├── main.py        # Price comparison entry point
├── comparator.py  # Cart building and savings ranking
├── matcher.py     # Claude-powered semantic offer matching
├── notifier.py    # HTML formatting and email delivery
├── scraper.py     # Marktguru offer scraping
├── sheet.py       # Google Sheets integration
└── models.py      # Shared data models
```

---

## About

Built as a learning project with Claude (Anthropic) as an AI pair programmer. The goal was hands-on experience with real APIs, clean Python architecture, and using LLMs as functional components in a pipeline — not just for chat.
