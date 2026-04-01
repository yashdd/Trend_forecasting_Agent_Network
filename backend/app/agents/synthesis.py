"""Synthesis Agent: LLM-generated summary, why it matters, industry impact for top topics."""
from datetime import datetime, timezone

from sqlalchemy import select, desc
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from app.db.session import get_sync_session
from app.models.orm import Topic, TopicAssignment, RawPost, Source, TrendInsight, TopicDailyMetric
from app.config import get_settings
from app.agents.state import TrendPipelineState


SYNTHESIS_PROMPT = """You are a trend analyst. You MUST only use facts that appear in the labeled sources below. Do not invent products, papers, or claims.

Topic: {topic_label}
Keywords: {keywords}

Evidence (each block is one post; cite using raw_post_id and URL exactly as given):
{snippets}

Rules:
- Every substantive claim in your answer must end with a bracket citation like [raw_post_id=123 url=<exact url>] using ONLY ids and URLs from the evidence blocks.
- If the evidence is thin, say so briefly instead of speculating.
- Do not cite sources that are not listed above.

Write exactly three short paragraphs:
1. What it is: 1-2 sentences describing the trend (each sentence with citations where applicable).
2. Why it matters: 1-2 sentences on significance (cited).
3. Potential industry impact: 1 sentence on who is affected and how (cited).

Format:
What it is: ...
Why it matters: ...
Potential impact: ...
"""


def run_synthesis(state: TrendPipelineState) -> TrendPipelineState:
    """For top-K topics by signal score, call LLM to generate summary, why_it_matters, industry_impact. Persist to trend_insights."""
    session = get_sync_session()
    try:
        settings = get_settings()
        top_k = getattr(settings, "pipeline_top_k_synthesis", 10)
        if not settings.google_api_key:
            return {**state, "synthesis_outputs": list(state.get("synthesis_outputs") or [])}

        # Top topics by recent signal_score (from topic_daily_metrics)
        recent = (
            session.execute(
                select(TopicDailyMetric.topic_id, TopicDailyMetric.signal_score)
                .where(TopicDailyMetric.signal_score.isnot(None))
                .order_by(desc(TopicDailyMetric.date))
            )
        ).all()
        # Dedupe by topic_id, take max signal_score
        from collections import defaultdict
        best: dict[int, float] = defaultdict(float)
        for tid, score in recent:
            if score is not None:
                best[tid] = max(best[tid], score)
        sorted_topics = sorted(best.items(), key=lambda x: -x[1])[: top_k]
        topic_ids = [t[0] for t in sorted_topics]

        if not topic_ids:
            return {**state, "synthesis_outputs": list(state.get("synthesis_outputs") or [])}

        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.3,
        )
        synthesis_outputs = list(state.get("synthesis_outputs") or [])
        now = datetime.now(timezone.utc)

        for topic_id in topic_ids:
            topic = session.execute(select(Topic).where(Topic.id == topic_id)).scalars().first()
            if not topic:
                continue
            # Representative posts: sample a few from this topic
            posts = (
                session.execute(
                    select(RawPost, Source.name)
                    .join(TopicAssignment, RawPost.id == TopicAssignment.raw_post_id)
                    .join(Source, RawPost.source_id == Source.id)
                    .where(TopicAssignment.topic_id == topic_id)
                    .limit(8)
                )
            ).all()
            snippets = []
            source_list = []
            cited_ids: list[int] = []
            for post, src_name in posts:
                snip = (post.title or "") + " " + (post.body or "")[:500]
                url = post.url or ""
                snippets.append(
                    f"[raw_post_id={post.id} source={src_name} url={url}]\n{snip.strip()[:400]}"
                )
                cited_ids.append(post.id)
            keywords = (topic.keywords or []) if isinstance(topic.keywords, list) else []
            prompt = SYNTHESIS_PROMPT.format(
                topic_label=topic.label or "Unknown",
                keywords=", ".join(keywords[:15]) if keywords else "N/A",
                snippets="\n---\n".join(snippets[:5]) or "No snippets",
            )
            try:
                msg = llm.invoke([HumanMessage(content=prompt)])
                text = msg.content if hasattr(msg, "content") else str(msg)
            except Exception:
                text = "Summary unavailable."
            # Parse three paragraphs
            summary = why = impact = ""
            for part in text.split("\n\n"):
                if part.strip().lower().startswith("what it is"):
                    summary = part.replace("What it is:", "").replace("what it is:", "").strip()
                elif part.strip().lower().startswith("why it matters"):
                    why = part.replace("Why it matters:", "").replace("why it matters:", "").strip()
                elif "impact" in part.strip().lower()[:30]:
                    impact = part.split(":", 1)[-1].strip() if ":" in part else part.strip()
            if not summary:
                summary = text[:1000]
            rep_sources = [{"url": p.url, "title": (p.title or "")[:200], "source": s} for p, s in posts[:5]]
            insight = TrendInsight(
                topic_id=topic_id,
                generated_at=now,
                summary=summary[:4000],
                why_it_matters=why[:2000] or None,
                industry_impact=impact[:2000] or None,
                representative_sources=rep_sources,
                llm_metadata={"model": settings.gemini_model},
            )
            session.add(insight)
            session.flush()
            synthesis_outputs.append({
                "trend_id": insight.id,
                "topic_id": topic_id,
                "summary": insight.summary,
                "why_it_matters": insight.why_it_matters,
                "industry_impact": insight.industry_impact,
                "representative_sources": rep_sources,
                "cited_raw_post_ids": cited_ids[:8],
            })
        session.commit()
        return {**state, "synthesis_outputs": synthesis_outputs}
    except Exception as e:
        session.rollback()
        return {**state, "error": str(e)}
    finally:
        session.close()
