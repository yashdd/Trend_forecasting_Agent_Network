# Agent Workflow (LangGraph)

## Graph Definition

The trend pipeline is implemented as a LangGraph `StateGraph` with a single path:

1. **ingestion** → **embedding_clustering** → **momentum** → **cross_source** → **synthesis** → END

## Shared State (TrendPipelineState)

- `raw_documents`: List of normalized docs from ingestion (id, source, external_id, title, body, url, created_at).
- `documents_with_embeddings`: Docs plus embedding vectors (used by downstream nodes).
- `topic_assignments`: List of (doc_id, topic_id) after clustering.
- `topic_metrics`: Per-topic daily metrics (mention_count, growth_rate, acceleration, signal_score).
- `cross_source_scores`: Map topic_id → cross-source strength (0–1).
- `synthesis_outputs`: List of trend insights (summary, why_it_matters, industry_impact, representative_sources).
- `error`: Set by any node on failure.
- `pipeline_run_id`: Optional run id for tracing.

## Nodes

| Node | Input | Output | Side effect |
|------|--------|--------|-------------|
| **ingestion** | (none) | raw_documents | Inserts into `raw_posts`, ensures `sources` rows |
| **embedding_clustering** | raw_documents (and DB) | documents_with_embeddings, topic_assignments | Inserts `embeddings`, `topics`, `topic_assignments` |
| **momentum** | topic_assignments + raw_posts | topic_metrics | Upserts `topic_daily_metrics` |
| **cross_source** | topic_assignments + raw_posts + sources | cross_source_scores | Upserts `cross_source_validation` |
| **synthesis** | top topics by signal_score | synthesis_outputs | Inserts `trend_insights` |

## Execution

- Triggered by APScheduler daily at 2:00 UTC, or via `POST /api/v1/admin/ingest`.
- A `PipelineRun` record is created with status `running`; on success it is set to `success` with `agent_steps` summary; on exception to `failed` with `error_message`.
- The graph is invoked with initial state `{ "raw_documents": [] }`; each node merges its result into state and passes it to the next.

## Optional Extensions

- **Conditional edge after ingestion**: If `len(raw_documents) == 0`, skip embedding and subsequent steps to save compute.
- **Retry edges**: On transient errors (e.g. rate limit), retry the same node once before failing.
