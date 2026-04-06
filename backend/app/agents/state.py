"""Shared state for the trend pipeline graph.

Keep graph state small: reference IDs and counts only. Full text, embeddings, and
metrics live in PostgreSQL; nodes load what they need via Session queries.
"""
from typing import TypedDict


class SynthesisOutput(TypedDict, total=False):
    trend_id: int
    topic_id: int
    summary: str
    why_it_matters: str
    industry_impact: str
    representative_sources: list

    # Traceability: raw_post ids echoed from DB for debugging (no bodies in state)
    cited_raw_post_ids: list[int]


class TrendPipelineState(TypedDict, total=False):
    # Ingestion: only new post IDs (capped); count for pipeline summaries
    ingested_new_post_ids: list[int]
    ingested_new_post_count: int

    # Embedding / clustering: no embedding vectors in state
    new_embeddings_created: int
    clustered_post_count: int
    topic_assignment_count: int

    # Momentum: rows written, not full daily series
    topic_daily_metrics_upserted: int

    cross_source_scores: dict[int, float]
    synthesis_outputs: list[SynthesisOutput]
    error: str
    pipeline_run_id: int
