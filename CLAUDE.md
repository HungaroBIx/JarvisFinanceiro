# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the Telegram bot:**
```bash
python -m bot.bot
```

**Run the Streamlit dashboard:**
```bash
streamlit run dashboard/app.py
```

**Environment setup:**
Copy `.env.example` to `.env` and fill in:
- `TELEGRAM_TOKEN` — from @BotFather
- `ANTHROPIC_API_KEY`
- `SUPABASE_URL` and `SUPABASE_KEY`

**Database setup:**
Run `supabase_schema.sql` once via Supabase Dashboard > SQL Editor to create the `gastos` table.

There are no test or lint commands configured.

## Architecture

This is a two-service app: a Telegram bot and a Streamlit dashboard, sharing a Supabase (PostgreSQL) backend.

### Telegram Bot (`bot/`)

- **`bot/bot.py`** — Entry point. Uses `python-telegram-bot` with a `ConversationHandler` that has two states: `AGUARDANDO` (waiting for input) and `CONFIRMANDO` (awaiting user confirmation). Commands: `/start`, `/relatorio`, `/cancelar`. Handlers for text and photo messages.
- **`bot/claude.py`** — Calls Claude API (`claude-sonnet-4-5`, max 256 tokens) to extract structured JSON (`valor`, `estabelecimento`, `categoria`, `data`) from either text descriptions or receipt images (base64-encoded). Returns `None` on failure.
- **`bot/db.py`** — Supabase client wrapper. `salvar_gasto()` inserts a row; `buscar_gastos()` queries with optional date/category filters.

**Flow:** User sends text or photo → Claude extracts expense JSON → bot shows parsed result with ✅/❌ inline keyboard → on confirm, saves to Supabase.

All DB and API calls inside the bot use `asyncio.to_thread()` since the Supabase and Anthropic clients are synchronous.

### Streamlit Dashboard (`dashboard/app.py`)

Reads from Supabase directly (via `@st.cache_resource` client). Renders sidebar filters (date range, categories), summary KPI cards, and three Plotly charts (line, pie, bar), plus an establishment-level aggregation table.

### Deployment

| Service | Platform |
|---------|----------|
| Bot | Railway (worker process via `Procfile`) |
| Dashboard | Streamlit Community Cloud |
| Database | Supabase |

### Categories

`CATEGORIAS` is defined identically in `bot/claude.py` (injected into Claude's prompts) and `dashboard/app.py` (sidebar filter). Keep both in sync when adding or renaming categories:

`Alimentação`, `Transporte`, `Moradia`, `Saúde`, `Lazer`, `Vestuário`, `Educação`, `Pet`, `Tecnologia`, `Serviços`, `Outros`
