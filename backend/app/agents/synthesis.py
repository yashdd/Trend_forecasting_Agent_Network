"""Synthesis Agent: LLM-generated summary, why it matters, industry impact for top topics.

Includes guardrails: JSON-shaped output, validation, retries with corrective prompts, and
deterministic fallbacks when the model fails checks.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import desc, func, or_, select

from app.agents.state import TrendPipelineState
from app.config import get_settings
from app.db.session import get_sync_session
from app.models.orm import RawPost, Source, Topic, TopicAssignment, TopicDailyMetric, TrendInsight

SYNTHESIS_JSON_PROMPT = """You are a trend analyst. Use ONLY facts from the evidence blocks below. Do not invent companies, products, paper titles, or URLs.

Topic: {topic_label}
Keywords: {keywords}

Evidence (each block is one post; you may ONLY cite these raw_post_id values and URLs):
{snippets}

Output a single JSON object with exactly these keys (strings only, no markdown):
{{
  "what_it_is": "1-2 sentences. Every substantive claim must end with a citation like [raw_post_id=123 url=<exact url from evidence>]",
  "why_it_matters": "1-2 sentences with the same citation style.",
  "potential_impact": "1 sentence: who is affected and how, with citations."
}}

Rules:
- Valid raw_post_id values for this task: {allowed_ids}
- Every paragraph must contain at least one valid [raw_post_id=... url=...] citation using ONLY ids and URLs from the evidence blocks.
- If evidence is too thin to support strong claims, say that briefly and still cite what exists.
- Do not output any text outside the JSON object.
"""

SYNTHESIS_RETRY_SUFFIX = """

Your previous answer failed validation: {failure_reason}
Return ONLY a corrected JSON object with the same three keys. Fix citations so they use ONLY allowed raw_post_id values and URLs from the evidence.
"""


def _strip_json_fence(raw: str) -> str:
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```\w*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _extract_cited_raw_post_ids(text: str) -> set[int]:
    out: set[int] = set()
    for m in re.finditer(r"\[raw_post_id=(\d+)", text):
        try:
            out.add(int(m.group(1)))
        except ValueError:
            continue
    return out


_BANNED_SUBSTRINGS = (
    "as a language model",
    "as an ai",
    "i cannot",
    "i can't",
    "i do not have",
    "i don't have",
    "i am not able",
    "i'm not able",
)


def _validate_synthesis_fields(
    what: str,
    why: str,
    impact: str,
    allowed_ids: set[int],
) -> tuple[bool, str]:
    parts = [what or "", why or "", impact or ""]
    if any(len(p.strip()) < 12 for p in parts):
        return False, "each field must be at least 12 characters"
    combined = " ".join(parts).lower()
    for b in _BANNED_SUBSTRINGS:
        if b in combined:
            return False, f"avoid meta-refusals and assistant disclaimers ({b!r})"
    cited = _extract_cited_raw_post_ids(" ".join(parts))
    if not cited:
        return False, "include at least one [raw_post_id=... url=...] citation from the evidence"
    if not cited.intersection(allowed_ids):
        return False, "citations must use raw_post_id values from the allowed list only"
    return True, ""


def _parse_json_synthesis(raw: str) -> dict[str, str] | None:
    s = _strip_json_fence(raw)
    try:
        data = json.loads(s)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    w = data.get("what_it_is")
    y = data.get("why_it_matters")
    p = data.get("potential_impact")
    if not all(isinstance(x, str) for x in (w, y, p)):
        return None
    return {"what_it_is": w.strip(), "why_it_matters": y.strip(), "potential_impact": p.strip()}


def _invoke_llm_with_retries(
    llm: ChatGoogleGenerativeAI,
    messages: list[HumanMessage],
    *,
    max_attempts: int,
) -> str:
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            msg = llm.invoke(messages)
            text = msg.content if hasattr(msg, "content") else str(msg)
            return text if isinstance(text, str) else str(text)
        except Exception as e:
            last_err = e
            if attempt < max_attempts - 1:
                time.sleep(min(2**attempt, 8))
    raise last_err if last_err else RuntimeError("LLM invoke failed")


def _keyword_fallback_posts(session: Any, topic: Topic, *, limit: int = 8) -> list[tuple[Any, str]]:
    """When TopicAssignment is empty, match recent raw_posts on label/keyword tokens (bounded)."""
    tokens: list[str] = []
    if topic.label:
        tokens.extend(re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", topic.label.replace("_", " ")))
    if isinstance(topic.keywords, list):
        for k in topic.keywords[:14]:
            if isinstance(k, str) and len(k.strip()) >= 3:
                tokens.append(k.strip())
    # Drop very short / duplicate tokens
    seen: set[str] = set()
    uniq: list[str] = []
    for t in tokens:
        tl = t.lower()
        if len(t) < 3 or tl in seen:
            continue
        seen.add(tl)
        uniq.append(t[:64])
        if len(uniq) >= 10:
            break
    if not uniq:
        return []

    def _esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    conds = []
    for tok in uniq:
        pat = f"%{_esc(tok)}%"
        conds.append(RawPost.title.ilike(pat))
        conds.append(RawPost.body.ilike(pat))
    rows = (
        session.execute(
            select(RawPost, Source.name)
            .join(Source, RawPost.source_id == Source.id)
            .where(or_(*conds))
            .order_by(desc(RawPost.fetched_at))
            .limit(limit)
        )
    ).all()
    return list(rows)


def _load_evidence_posts(session: Session, topic_id: int, topic: Topic) -> list[tuple[Any, str]]:
    rows = (
        session.execute(
            select(RawPost, Source.name)
            .join(TopicAssignment, RawPost.id == TopicAssignment.raw_post_id)
            .join(Source, RawPost.source_id == Source.id)
            .where(TopicAssignment.topic_id == topic_id)
            .limit(8)
        )
    ).all()
    if rows:
        return list(rows)
    return _keyword_fallback_posts(session, topic, limit=8)


def _fallback_from_posts(posts: list[tuple[Any, str]]) -> tuple[str, str, str]:
    """Deterministic summary when LLM is unavailable or invalid. Requires at least one post."""
    if not posts:
        raise ValueError("fallback_from_posts requires non-empty posts")
    lines = []
    for post, src in posts[:3]:
        title = (post.title or "").strip() or "Untitled"
        url = (post.url or "").strip()
        lines.append(f"[raw_post_id={post.id} url={url}] {src}: {title[:180]}")
    block = " ".join(lines)
    summary = f"Sources discuss related items, including: {block[:900]}"
    why = f"Multiple mentions in developer and research channels suggest active interest; see citations above."
    impact = f"Watch for follow-on discussion in the same communities cited above [raw_post_id={posts[0][0].id} url={(posts[0][0].url or '')[:500]}]."
    return summary[:4000], why[:2000], impact[:2000]


def run_synthesis(state: TrendPipelineState) -> TrendPipelineState:
    """For top-K topics by signal score, call LLM to generate summary, why_it_matters, industry_impact."""
    session = get_sync_session()
    try:
        settings = get_settings()
        top_k = getattr(settings, "pipeline_top_k_synthesis", 10)
        max_retries = settings.synthesis_max_retries
        temperature = settings.synthesis_temperature
        if not settings.google_api_key:
            return {**state, "synthesis_outputs": list(state.get("synthesis_outputs") or [])}

        # Topics must have *current* TopicAssignment rows. Old metrics can linger for topic_ids
        # that BERTopic no longer assigns posts to — that caused empty evidence and the
        # "Not enough source text…" fallback for most signals.
        assigned_rows = session.execute(select(TopicAssignment.topic_id, func.count()).group_by(TopicAssignment.topic_id)).all()
        assigned_topic_ids = {tid for tid, _ in assigned_rows if tid is not None}

        recent = (
            session.execute(
                select(TopicDailyMetric.topic_id, TopicDailyMetric.signal_score)
                .where(TopicDailyMetric.signal_score.isnot(None))
                .order_by(desc(TopicDailyMetric.date))
            )
        ).all()
        from collections import defaultdict

        best: dict[int, float] = defaultdict(float)
        for tid, score in recent:
            if tid is None or tid not in assigned_topic_ids:
                continue
            if score is not None:
                best[tid] = max(best[tid], score)
        sorted_topics = sorted(best.items(), key=lambda x: -x[1])[:top_k]
        topic_ids = [t[0] for t in sorted_topics]

        if not topic_ids:
            return {**state, "synthesis_outputs": list(state.get("synthesis_outputs") or [])}

        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )
        synthesis_outputs = list(state.get("synthesis_outputs") or [])
        now = datetime.now(timezone.utc)

        for topic_id in topic_ids:
            topic = session.execute(select(Topic).where(Topic.id == topic_id)).scalars().first()
            if not topic:
                continue
            if (topic.label or "").strip().lower() == "outlier":
                continue

            posts = _load_evidence_posts(session, topic_id, topic)
            snippets = []
            cited_ids: list[int] = []
            for post, src_name in posts:
                snip = (post.title or "") + " " + (post.body or "")[:500]
                url = post.url or ""
                snippets.append(
                    f"[raw_post_id={post.id} source={src_name} url={url}]\n{snip.strip()[:400]}"
                )
                cited_ids.append(post.id)
            allowed_ids = set(cited_ids)
            allowed_ids_str = ", ".join(str(i) for i in cited_ids[:20]) if cited_ids else "(none)"
            keywords = (topic.keywords or []) if isinstance(topic.keywords, list) else []

            if not cited_ids:
                # No assignment match and keyword fallback found nothing — skip insight (no boilerplate row).
                continue

            base_prompt = SYNTHESIS_JSON_PROMPT.format(
                topic_label=topic.label or "Unknown",
                keywords=", ".join(keywords[:15]) if keywords else "N/A",
                snippets="\n---\n".join(snippets[:5]) or "No snippets",
                allowed_ids=allowed_ids_str,
            )

            messages: list[HumanMessage] = [HumanMessage(content=base_prompt)]
            parsed: dict[str, str] | None = None
            validation_ok = False
            failure_reason = ""
            last_raw = ""
            attempts_used = 0

            for attempt in range(max(1, max_retries)):
                attempts_used = attempt + 1
                try:
                    last_raw = _invoke_llm_with_retries(llm, messages, max_attempts=2)
                except Exception as e:
                    last_raw = ""
                    failure_reason = f"model_error: {e!s}"
                    break

                parsed = _parse_json_synthesis(last_raw)
                if not parsed:
                    failure_reason = "invalid JSON or missing keys what_it_is / why_it_matters / potential_impact"
                    messages.append(HumanMessage(content=SYNTHESIS_RETRY_SUFFIX.format(failure_reason=failure_reason)))
                    continue

                ok, reason = _validate_synthesis_fields(
                    parsed["what_it_is"],
                    parsed["why_it_matters"],
                    parsed["potential_impact"],
                    allowed_ids,
                )
                if ok:
                    validation_ok = True
                    break
                failure_reason = reason
                messages.append(HumanMessage(content=SYNTHESIS_RETRY_SUFFIX.format(failure_reason=failure_reason)))

            if validation_ok and parsed:
                summary = parsed["what_it_is"]
                why = parsed["why_it_matters"]
                impact = parsed["potential_impact"]
                meta_status = "ok"
            else:
                summary, why, impact = _fallback_from_posts(posts)
                meta_status = "fallback"
                if not validation_ok:
                    meta_status = f"fallback_after_validation:{failure_reason[:200]}"

            rep_sources = [{"url": p.url, "title": (p.title or "")[:200], "source": s} for p, s in posts[:5]]
            insight = TrendInsight(
                topic_id=topic_id,
                generated_at=now,
                summary=summary[:4000],
                why_it_matters=why[:2000] or None,
                industry_impact=impact[:2000] or None,
                representative_sources=rep_sources,
                llm_metadata={
                    "model": settings.gemini_model,
                    "synthesis_status": meta_status,
                    "synthesis_attempts": attempts_used,
                    "validation_ok": validation_ok,
                    "last_failure": failure_reason[:500] if not validation_ok else None,
                },
            )
            session.add(insight)
            session.flush()
            synthesis_outputs.append(
                {
                    "trend_id": insight.id,
                    "topic_id": topic_id,
                    "summary": insight.summary,
                    "why_it_matters": insight.why_it_matters,
                    "industry_impact": insight.industry_impact,
                    "representative_sources": rep_sources,
                    "cited_raw_post_ids": cited_ids[:8],
                }
            )
        session.commit()
        return {**state, "synthesis_outputs": synthesis_outputs}
    except Exception as e:
        session.rollback()
        return {**state, "error": str(e)}
    finally:
        session.close()
