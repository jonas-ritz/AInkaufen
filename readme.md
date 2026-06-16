# AInkaufen

A weekly grocery price optimizer that tells you which supermarket saves you the most money.

I built this as a side project to learn more about API integration and AI-powered workflows — using Claude as a pair programmer throughout the whole thing.

---

## What it does

- Reads your grocery list from Google Sheets (checkboxes for what you need this week)
- Scrapes current offers from local supermarkets via Marktguru
- Uses Claude to match your items to the right offers (so "milk" doesn't match "chocolate milk")
- Ranks supermarkets by total savings
- Sends you an email summary every day

---

## Stack

- Python 3.11
- Anthropic Claude API — for semantic product matching
- Google Sheets API — grocery list input
- Marktguru API — supermarket offer data
- SMTP (smtplib) — daily email notifications
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
SMTP_USER=your-gmail-address@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
EMAIL_TO=JonasRitz1998@web.de
PLZ=52428
```

`SMTP_USER`/`SMTP_PASSWORD` are the credentials of the account that *sends* the email (e.g. a Gmail account with an [App Password](https://myaccount.google.com/apppasswords)). `EMAIL_TO` is the recipient address.

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

Runs daily via [.github/workflows/daily.yml](.github/workflows/daily.yml). Add these repository secrets under
*Settings → Secrets and variables → Actions*:

- `ANTHROPIC_API_KEY`
- `SHEET_ID`
- `GOOGLE_CREDENTIALS` (contents of your `credentials.json`)
- `SMTP_USER` / `SMTP_PASSWORD` (sender account)
- `SMTP_HOST` / `SMTP_PORT` (optional, defaults to Gmail's `smtp.gmail.com:587`)
- `EMAIL_TO` (optional, defaults to `JonasRitz1998@web.de`)
- `PLZ` (optional)

---

## About

Built as a learning project with Claude (Anthropic) as an AI pair programmer. The goal was to get hands-on experience with real APIs, clean Python architecture, and using LLMs as functional components in a pipeline — not just for chat.
