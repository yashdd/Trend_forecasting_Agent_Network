# API Design

Base URL: `/api/v1`. All responses JSON unless noted.

## Health

- **GET /health**  
  Returns `{ "status": "ok", "database": "connected" }` or degraded with detail.  
  (Mounted at app root, not under `/api/v1`.)

## Signals

- **GET /api/v1/signals**  
  Real-time signal feed.  
  Query: `limit` (default 20), `min_score` (0–1), `since` (ISO8601).  
  Response: Array of signal objects with `id`, `topic_id`, `topic_label`, `signal_score`, `cross_source_strength`, `novelty_score`, `predicted_impact`, `summary`, `sources[]`, `first_detected_at`, `updated_at`.

- **GET /api/v1/signals/{signal_id}**  
  Single trend deep-dive (same shape as one element of the list).

## Topics

- **GET /api/v1/topics**  
  Trending topics.  
  Query: `days` (default 7), `sort` (momentum | signal_score | novelty), `limit` (default 50).  
  Response: Array of `{ id, label, keywords, signal_score, cross_source_strength, mention_count, first_seen_at }`.

- **GET /api/v1/topics/{topic_id}**  
  Topic detail: `daily_metrics[]`, `trend_insight` (summary, why_it_matters, industry_impact, representative_sources).

- **GET /api/v1/topics/{topic_id}/discussions**  
  Paginated raw discussions and research refs.  
  Query: `limit` (default 50).  
  Response: Array of `{ id, source, url, title, body, author, created_at }`.

## Metrics

- **GET /api/v1/metrics/momentum**  
  Time-series for topic momentum.  
  Query: `topic_id` (required), `from`, `to` (ISO date).  
  Response: Array of `{ date, mention_count, signal_score, growth_rate }`.

## Reports

- **GET /api/v1/reports/weekly**  
  List weekly reports.  
  Response: Array of `{ id, period_start, period_end, created_at }`.

- **GET /api/v1/reports/weekly/{report_id}**  
  Full report: `top_signals`, `report_markdown`, period, created_at.

## Admin

- **POST /api/v1/admin/ingest**  
  Trigger full pipeline (ingestion through synthesis). Runs in background; returns `{ "status": "accepted", "message": "Pipeline started in background." }`.

## OpenAPI

- Swagger UI: `/docs`
- ReDoc: `/redoc`
