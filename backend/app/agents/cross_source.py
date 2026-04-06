"""Cross-Source Validation Agent: verify topic appears on multiple sources; set confidence."""
from datetime import date, datetime, timezone, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models.orm import Topic, TopicAssignment, RawPost, Source, CrossSourceValidation
from app.agents.state import TrendPipelineState


def run_cross_source_validation(state: TrendPipelineState) -> TrendPipelineState:
    """
    For each topic and recent date: count distinct sources across all 10 platforms.
    Set cross_source_strength = n_sources / 10 (0-1). Persist to cross_source_validation.
    """
    session = get_sync_session()
    try:
        # (topic_id, date) -> set of source names
        q = (
            select(
                TopicAssignment.topic_id,
                func.date(RawPost.created_at).label("day"),
                Source.name,
            )
            .join(RawPost, TopicAssignment.raw_post_id == RawPost.id)
            .join(Source, RawPost.source_id == Source.id)
            .where(RawPost.created_at.isnot(None))
        )
        rows = session.execute(q).all()
        if not rows:
            return {**state, "cross_source_scores": dict(state.get("cross_source_scores") or {})}

        from collections import defaultdict
        topic_date_sources: dict[tuple[int, date], set[str]] = defaultdict(set)
        for topic_id, day, source_name in rows:
            if day and source_name:
                topic_date_sources[(topic_id, day)].add(source_name)

        cross_scores = dict(state.get("cross_source_scores") or {})
        now = datetime.now(timezone.utc)
        for (topic_id, day), sources in topic_date_sources.items():
            n = len(sources)
            strength = round(min(n / 10.0, 1.0), 4) if n else 0.0
            cross_scores[topic_id] = max(cross_scores.get(topic_id, 0), strength)

            existing = session.execute(
                select(CrossSourceValidation).where(
                    CrossSourceValidation.topic_id == topic_id,
                    CrossSourceValidation.date == day,
                )
            ).scalars().first()
            if existing:
                existing.sources_present = list(sources)
                existing.cross_source_strength = strength
                existing.validated_at = now
            else:
                session.add(
                    CrossSourceValidation(
                        topic_id=topic_id,
                        date=day,
                        sources_present=list(sources),
                        cross_source_strength=strength,
                        validated_at=now,
                    )
                )
        session.commit()
        return {**state, "cross_source_scores": cross_scores}
    except Exception as e:
        session.rollback()
        return {**state, "error": str(e)}
    finally:
        session.close()
