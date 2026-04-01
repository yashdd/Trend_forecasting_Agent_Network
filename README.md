# Trend Forecasting Agent Network

Production-grade trend intelligence platform that detects emerging technology trends 3–5 days before mainstream coverage by analyzing Reddit, Hacker News, and arXiv.

## Stack

- **Backend:** FastAPI, PostgreSQL, pgvector, LangGraph
- **Agents:** Data Ingestion, Embedding/Clustering (BERTopic/HDBSCAN), Momentum Scoring, Cross-Source Validation, Synthesis (LLM)
- **Frontend:** React + TailwindCSS + Recharts
- **Scheduler:** APScheduler for daily pipeline

## Quick start

1. Copy `.env.example` to `.env` and set `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `OPENAI_API_KEY` as needed.
2. Start services: `docker-compose up -d postgres` then run backend locally, or `docker-compose up -d` for full stack.
3. Run migrations: `cd backend && alembic upgrade head`.
4. Start backend: `uvicorn app.main:app --reload`.
5. Start frontend: `cd frontend && npm install && npm run dev`.

## Project structure

- `backend/` — FastAPI app, agents, DB, API
- `frontend/` — Dashboard, Signal Feed, Reports
- `docs/` — Architecture, schema, API, example report

## License

MIT
