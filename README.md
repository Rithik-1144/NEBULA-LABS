# Nebula KnowLab Supermarket Operations Agent

This repository contains a production-minded supermarket operations agent built around a Telegram-first workflow, deterministic business services, and a seeded demo store. The project is intentionally structured to be extensible, with a clear separation between agent reasoning, business logic, persistence, and presentation.

## Overview

The application is designed for a kirana supermarket owner to operate the store with natural language in Telegram. It supports stock updates, billing, khata tracking, GST-aware calculations, daily close summaries, and document generation.

## Technology Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x
- Pydantic v2
- PostgreSQL-ready config with SQLite fallback for local dev
- python-telegram-bot
- reportlab for PDF generation
- python-pptx for presentation output
- Pytest for automated verification

## Architecture

```mermaid
flowchart TD
    U[Store Owner] --> T[Telegram]
    T --> A[AI Agent]
    A --> TR[Tool Registry]
    TR --> I[Inventory Tools]
    TR --> B[Billing Tools]
    TR --> K[Khata Tools]
    TR --> P[Payment Tools]
    TR --> AN[Analytics Tools]
    TR --> D[Document Tools]
    I --> DB[(Database)]
    B --> DB
    K --> DB
    P --> DB
    AN --> DB
    D --> PDF[PDF Invoice]
    D --> PPT[PPTX Report]
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run locally

```bash
uvicorn app.main:app --reload
```

## Telegram bot

1. Open Telegram and message `@BotFather`.
2. Run `/newbot`, choose a display name and username, then copy the token.
3. Put the token in `.env` as `TELEGRAM_BOT_TOKEN=...`.
4. Optionally set `AUTHORIZED_TELEGRAM_USER_IDS` to a comma-separated list of Telegram numeric user IDs.
5. Restart the app. The bot uses polling automatically when a token is configured.

Supported commands include `/start`, `/help`, `/status`, `/new`, and `/cancel`. Natural-language requests such as `How much Maggi left?`, `Create a draft bill`, `Create customer Maya 9876543210`, and `Finalize bill 12` are routed through the same store services as the dashboard. Finalized invoices are returned as PDF documents.

## Testing

```bash
pytest -q
```

## Notes

This is a structured, enterprise-style foundation for the requested supermarket agent and intentionally keeps the core logic deterministic and service-backed rather than relying on LLM-generated business math.
