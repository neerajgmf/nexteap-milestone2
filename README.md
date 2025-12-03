# NextLeap Milestone 2 – AI Review Pulse

An end-to-end workflow that ingests Google Play & App Store reviews, removes PII, discovers emerging themes with LLMs, stores structured feedback in Supabase, and assembles weekly “pulse” packages (HTML/Markdown/email) for product teams.

## What’s Inside
- **Ingestion (`src/scraper.py`)** – pulls hundreds of fresh reviews per store, deduplicates with SHA-256 hashes, and optionally upserts into Supabase plus timestamped CSVs under `artifacts/reviews/`.
- **Intelligence (`src/themer.py`, `src/note_generator.py`, `src/analyzer.py`)** – filters PII, discovers <5 high-signal themes via OpenRouter or Gemini, classifies each review, extracts quotes, and generates action recommendations.
- **Storytelling (`src/email_drafter.py`, `src/mailer.py`)** – turns summaries into HTML/Markdown pulses and Resend-ready emails with branded theming.
- **Delivery surface (`api/analyze.py`, `api/cron.py`, `public/`, `local_server.py`)** – lightweight API + static UI that can run on Vercel or locally for self-serve analyses, plus cron-friendly automation.

```
Stores → scraper → pandas cleanup → Supabase / CSV
           ↓
      themer + PII filter → classified dataframe
           ↓
  note_generator → pulse markdown/html
           ↓
 email_drafter / mailer → Resend / artifacts/emails
```

## Repository Tour
```
.
├── src/
│   ├── scraper.py          # Cross-store ingestion & persistence helpers
│   ├── themer.py           # Theme discovery, classification, sentiment labeling
│   ├── note_generator.py   # Weekly pulse assembly + outputs
│   ├── email_drafter.py    # Draft/send rich email pulses via Resend
│   ├── mailer.py           # Lightweight HTML email used by API cron endpoints
│   ├── analyzer.py         # Gemini JSON analysis for quick insights
│   └── config.py           # Central config + defaults (INDmoney IDs, etc.)
├── api/                    # Vercel-style handlers (`/api/analyze`, `/api/cron`)
├── public/                 # Static UI served by `local_server.py`
├── artifacts/              # Generated CSVs, pulses, and email drafts
├── tests/, test_*.py       # Pytest suites covering ingestion → pulse → email
├── docs/STEP*.md           # Milestone-by-milestone build notes
└── supabase_schema.sql     # Table structure for `reviews`
```

## Getting Started
### Prerequisites
- Python 3.10+ (repository virtualenv uses 3.13)
- Supabase project (optional but required for persistence & pulse generation defaults)
- At least one LLM provider: OpenRouter API key **or** Google Gemini key
- Resend API key (only needed for actual email delivery)

### Installation
```bash
git clone <repo-url>
cd nextleap-milestone2
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Environment Variables
Create a `.env` file in the repo root and supply the values that apply to your workflow.

| Variable | Required | Purpose / Notes |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | optional | Enables OpenRouter (Claude, GPT-4o, etc.) for theming |
| `OPENROUTER_MODEL` | optional | Defaults to `google/gemini-2.0-flash-001` if unset |
| `GEMINI_API_KEY` | optional | Used when OpenRouter is not configured |
| `RESEND_API_KEY` | optional | Required to actually send pulse emails |
| `SENDER_EMAIL` | optional | Defaults to `onboarding@resend.dev` |
| `RECIPIENT_EMAIL` | optional | Default target for cron/tests (override per run) |
| `NEXT_PUBLIC_SUPABASE_URL` | optional | Supabase project URL for persistence |
| `SUPABASE_SERVICE_ROLE_KEY` | optional | Preferred for server-side calls (falls back to anon key) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | optional | Used if service key missing |
| `PRODUCT_NAME` | optional | Defaults to `IND MONEY` (shown in reports/emails) |
| `GOOGLE_PLAY_ID` | optional | Defaults to `in.indwealth` |
| `APP_STORE_ID` | optional | Defaults to `1450178837` |
| `APP_STORE_COUNTRY` | optional | Country code for App Store RSS (default `in`) |

> ✅ Only one LLM provider is required. `Config.get_llm_provider()` automatically selects OpenRouter first, then Gemini.

## Core Workflows
### 1. End-to-end smoke test
Runs ingestion → Gemini JSON analysis → HTML email preview saved to `test_report.html`.
```bash
python test_run.py
```

### 2. Ingest the latest 12 weeks of reviews
```bash
python - <<'PY'
from src.scraper import run_ingestion
df = run_ingestion(weeks=12, save_db=True, save_csv=True)
print(df.head())
PY
```
Outputs:
- Supabase upsert (if credentials exist)
- Timestamped CSV under `artifacts/reviews/`
- `pandas` DataFrame in-memory for further processing

### 3. Theme extraction & pulse generation
```bash
python -m src.note_generator --weeks 1 --output-dir artifacts/pulses
```
This command loads classified reviews from Supabase (or classifies on the fly), pulls top 3 issues, quotes, AI-generated actions, and saves both Markdown + HTML into `artifacts/pulses/`.

### 4. Draft or send weekly pulse emails
```bash
# Draft only (HTML/TXT saved under artifacts/emails/)
python -m src.email_drafter --weeks 1

# Draft + send via Resend to a custom address
python -m src.email_drafter --weeks 1 --send --to exec@example.com
```
CLI flow calls `note_generator.generate_weekly_pulse`, builds HTML/text bodies, optionally hits Resend, and always saves local drafts.

### 5. Debug individual scrapers
```bash
python debug_scraper.py
```
Prints counts + sample rows for both Google Play and App Store fetchers so you can quickly verify store IDs, connectivity, or rate limits.

## Local API & UI
- `local_server.py` serves `public/index.html` plus proxies `/api/analyze` requests to `api/analyze.handler`.  
  ```bash
  python local_server.py
  ```
  Visit `http://localhost:8000`, paste an app-store URL + email, and the handler will ingest, analyze, and email results (respecting your `.env`).
- `api/cron.py` can be scheduled (e.g., Vercel cron) to run the weekly job with config defaults.

## Supabase Schema
Use `supabase_schema.sql` to provision the `reviews` table locally:
```bash
psql $SUPABASE_DB_URL -f supabase_schema.sql
```
`note_generator.generate_weekly_pulse()` expects classified rows with at least `content`, `source`, `rating`, and optionally `topics`.

## Testing
```bash
pytest
```
Key suites:
- `tests/test_scraper.py`, `tests/test_analyzer.py`, etc. – unit coverage
- `test_integration.py` – orchestration path (ingest → classify → pulse)
- `test_mailer.py`, `test_email_drafter.py` – email rendering & draft regression

## Troubleshooting & Tips
- **Rate limits / empty feeds** – App Store RSS tops out ~50 reviews; Google Play `count` defaults to 500. Adjust via `run_ingestion(gp_count=...)`.
- **LLM costs** – Theme discovery/classification batches reviews in groups of 20. Reduce sample sizes or disable OpenRouter keys when experimenting offline.
- **Supabase optional** – If credentials are missing, ingestion skips DB writes and downstream pulse generation must be provided with a DataFrame manually.
- **Artifacts hygiene** – Generated files accumulate under `artifacts/`; prune or add to `.gitignore` as needed.
- **Docs** – The `docs/STEP*.md` files contain milestone-by-milestone reasoning if you need a narrative of how the system evolved.

Happy shipping! 🎯

