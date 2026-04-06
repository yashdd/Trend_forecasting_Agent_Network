"""Momentum Scoring Agent: mention counts per topic per day, growth rate, acceleration, signal score."""
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models.orm import TopicAssignment, RawPost, Source, TopicDailyMetric
from app.agents.state import TrendPipelineState


def run_momentum(state: TrendPipelineState) -> TrendPipelineState:
    """
    For each topic, compute per-day mention counts (by raw_post.created_at date).
    Compute growth_rate and acceleration; set signal_score (e.g. weighted combo).
    Persist to topic_daily_metrics.
    """
    session = get_sync_session()
    try:
        # TopicAssignment -> RawPost: get date from raw_post.created_at
        # Count (topic_id, date) and aggregate
        q = (
            select(
                TopicAssignment.topic_id,
                func.date(RawPost.created_at).label("day"),
                RawPost.source_id,
            )
            .join(RawPost, TopicAssignment.raw_post_id == RawPost.id)
            .where(RawPost.created_at.isnot(None))
        )
        rows = session.execute(q).all()
        if not rows:
            return {**state, "topic_daily_metrics_upserted": 0}

        # Aggregate: (topic_id, date) -> count; (topic_id, date) -> {source_id: count}
        from collections import defaultdict
        counts: dict[tuple[int, date], int] = defaultdict(int)
        by_source: dict[tuple[int, date], dict[int, int]] = defaultdict(lambda: defaultdict(int))
        for topic_id, day, source_id in rows:
            if day is None:
                continue
            key = (topic_id, day)
            counts[key] += 1
            by_source[key][source_id] = by_source[key].get(source_id, 0) + 1

        # Resolve source_id -> name for source_breakdown
        source_ids = set()
        for (_, _), sd in by_source.items():
            source_ids.update(sd.keys())
        source_names = {}
        if source_ids:
            for row in session.execute(select(Source.id, Source.name).where(Source.id.in_(source_ids))).all():
                source_names[row[0]] = row[1]

        metrics_written = 0

        for (topic_id, day), mention_count in counts.items():
            breakdown = by_source.get((topic_id, day), {})
            source_breakdown = {source_names.get(sid, str(sid)): c for sid, c in breakdown.items()}

            # Discrete-time velocity / acceleration (day granularity): Δmentions/Δdays vs prior days.
            # For a smoother d/dt proxy over window W: v_W = (M_t - M_{t-W}) / W with M = cumulative or rolling sum.
            prev_counts = []
            for d in [day - timedelta(days=1), day - timedelta(days=2)]:
                prev_counts.append(counts.get((topic_id, d), 0))
            prev_count_1 = prev_counts[0] if len(prev_counts) >= 1 else 0
            prev_count_2 = prev_counts[1] if len(prev_counts) >= 2 else 0
            growth_rate = (mention_count - prev_count_1) / (prev_count_1 + 1e-6)
            growth_prev = (prev_count_1 - prev_count_2) / (prev_count_2 + 1e-6)
            acceleration = growth_rate - growth_prev
            # Novelty baseline: compare to last 7 days average for this topic.
            hist_days = [day - timedelta(days=i) for i in range(1, 8)]
            hist_counts = [counts.get((topic_id, d), 0) for d in hist_days]
            baseline = (sum(hist_counts) / max(1, len(hist_counts))) if hist_counts else 0.0
            novelty = (mention_count - baseline) / (baseline + 1.0)

            # Smooth: simple clamp + combine volume, novelty, and acceleration
            vol = min(1.0, mention_count / 60.0)
            nov = max(0.0, min(1.0, novelty / 3.0))
            acc = max(0.0, min(1.0, acceleration))
            raw_score = (vol * 0.35) + (nov * 0.35) + (acc * 0.30)
            signal_score = round(min(1.0, max(0.0, raw_score)), 4)

            existing = session.execute(
                select(TopicDailyMetric).where(
                    TopicDailyMetric.topic_id == topic_id,
                    TopicDailyMetric.date == day,
                )
            ).scalars().first()
            if existing:
                existing.mention_count = mention_count
                existing.growth_rate = growth_rate
                existing.acceleration = acceleration
                existing.signal_score = signal_score
                existing.source_breakdown = source_breakdown
            else:
                session.add(
                    TopicDailyMetric(
                        topic_id=topic_id,
                        date=day,
                        mention_count=mention_count,
                        growth_rate=growth_rate,
                        acceleration=acceleration,
                        signal_score=signal_score,
                        source_breakdown=source_breakdown,
                    )
                )
            metrics_written += 1
        session.commit()
        return {**state, "topic_daily_metrics_upserted": metrics_written}
    except Exception as e:
        session.rollback()
        return {**state, "error": str(e)}
    finally:
        session.close()
