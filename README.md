# Trend Forecasting Agent Network

A trend intelligence app that turns noisy internet chatter into a **ranked feed of early signals**.

It ingests posts from multiple platforms, clusters them into topics, scores “how hot” they are, and produces short, sourced summaries.

## What you get

- **Signals feed**: “what’s emerging right now” with score + sources + simple explainability (“Explain like I’m 5”)
- **Dashboard**: trending topics + momentum chart
- **Topic deep-dive**: raw discussions/research links + insight summary
- **Weekly reports**: auto-generated markdown report
- **Alerts**: create webhook rules (Slack/Discord/custom) with recent event log

## Data sources (10)

- Reddit (optional credentials)
- Hacker News
- arXiv
- GitHub (optional token)
- Product Hunt (token required)
- Tech RSS (multiple outlets)
- Stack Overflow
- Dev.to
- Lobste.rs
- Google Trends

## How it works (simple)

1. **Ingest**: fetch new items and store as `raw_posts`
2. **Embed + cluster**: convert text → vectors and group into topics
3. **Score**: compute momentum + novelty signals (0–1)
4. **Cross-source**: how many different places talk about it
5. **Categorize**: assign one of 10 human categories
6. **Synthesize**: Gemini generates a short “what/why/impact”

## Tech stack

- **Backend**: FastAPI, SQLAlchemy, Alembic, PostgreSQL, pgvector
- **Pipeline**: LangGraph agents + APScheduler
- **Embeddings/Topics**: sentence-transformers + BERTopic/HDBSCAN
- **LLM**: Google Gemini (`GOOGLE_API_KEY`, `GEMINI_MODEL`)
- **Frontend**: React + Vite + Tailwind + React Query + Recharts

## Quickstart (local)

### 1) Configure environment

Copy example env:

```bash
cp .env.example .env
```

Fill at minimum:
- `DATABASE_URL`, `DATABASE_URL_SYNC`
- `GOOGLE_API_KEY`, `GEMINI_MODEL`

Optional:
- `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` (if you can create a Reddit app)
- `GITHUB_TOKEN` (higher rate limits)
- `PRODUCTHUNT_API_TOKEN` (required to ingest Product Hunt)

### 2) Backend

From `backend/`:

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

### 3) Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

Vite proxies `/api/*` to the backend. If your backend runs on a different port, update `frontend/vite.config.ts`.

### 4) Run the pipeline

- In the UI: click **Run pipeline now**
- Or call:

```bash
curl -X POST http://127.0.0.1:8004/api/v1/admin/ingest
```

## Useful endpoints

- `GET /health`
- `GET /api/v1/signals`
- `GET /api/v1/topics`
- `GET /api/v1/explain/topic/{topic_id}`
- `GET /api/v1/runs/latest`
- `GET /api/v1/search?q=...`
- `GET /api/v1/exports/signals.csv`

## Alerts (webhooks)

Create a rule in the UI (Alerts tab). The backend evaluates rules every ~10 minutes and sends JSON to your webhook URL.

## Databricks (optional, background)

If you want the backend to trigger a Databricks Job every 24h:

```env
USE_DATABRICKS_JOBS=true
DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
DATABRICKS_TOKEN=<PAT>
DATABRICKS_PIPELINE_JOB_ID=<job_id>
```

Restart the backend after changing env vars.

## Security notes

- `.env` is ignored by `.gitignore`. **Never commit it.**
- If you ever accidentally committed tokens, rotate them immediately (Google/GitHub/ProductHunt).

