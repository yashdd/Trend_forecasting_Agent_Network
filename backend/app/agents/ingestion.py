"""Data Ingestion Agent: fetch from all 10 sources; clean and store."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models.orm import Source, RawPost
from app.services.reddit_client import RedditClient
from app.services.hn_client import HNClient
from app.services.arxiv_client import ArxivClient
from app.services.github_client import GitHubClient
from app.services.producthunt_client import ProductHuntClient
from app.services.rss_client import RSSClient
from app.services.stackoverflow_client import StackOverflowClient
from app.services.devto_client import DevToClient
from app.services.lobsters_client import LobstersClient
from app.services.google_trends_client import GoogleTrendsClient
from app.agents.state import TrendPipelineState

log = logging.getLogger(__name__)

# Cap IDs kept in LangGraph state to avoid huge checkpoints / memory.
_MAX_IDS_IN_STATE = 500

# (callable_returning_items, source_name)
_SOURCE_REGISTRY: list[tuple[str, callable]] = [
    ("reddit",        lambda: RedditClient().fetch_posts()),
    ("hackernews",    lambda: HNClient().fetch_stories()),
    ("arxiv",         lambda: ArxivClient().fetch_abstracts()),
    ("github",        lambda: GitHubClient().fetch_repos()),
    ("producthunt",   lambda: ProductHuntClient().fetch_posts()),
    ("rss_news",      lambda: RSSClient().fetch_articles()),
    ("stackoverflow", lambda: StackOverflowClient().fetch_questions()),
    ("devto",         lambda: DevToClient().fetch_articles()),
    ("lobsters",      lambda: LobstersClient().fetch_stories()),
    ("google_trends", lambda: GoogleTrendsClient().fetch_trends()),
]


def _get_or_create_source(session: Session, name: str, config: dict | None = None) -> int:
    row = session.execute(select(Source).where(Source.name == name)).scalars().first()
    if row:
        return row.id
    src = Source(name=name, config=config)
    session.add(src)
    session.flush()
    return src.id


def run_ingestion(state: TrendPipelineState) -> TrendPipelineState:
    """Fetch from all sources, dedupe, store in raw_posts. State carries only new post IDs (capped)."""
    session = get_sync_session()
    try:
        new_ids: list[int] = list(state.get("ingested_new_post_ids") or [])
        now = datetime.now(timezone.utc)
        inserted_this_run = 0
        per_source_new: dict[str, int] = dict(state.get("ingested_new_by_source") or {})

        for source_name, fetcher in _SOURCE_REGISTRY:
            sid = _get_or_create_source(session, source_name)
            try:
                items = fetcher()
            except Exception as exc:
                log.warning("Source %s failed: %s", source_name, exc)
                continue
            log.info("Source %s returned %d items", source_name, len(items))
            for item in items:
                existing = session.execute(
                    select(RawPost).where(
                        RawPost.source_id == sid,
                        RawPost.external_id == item["external_id"],
                    )
                ).scalars().first()
                if existing:
                    continue
                post = RawPost(
                    source_id=sid,
                    external_id=item["external_id"],
                    url=item.get("url"),
                    title=item.get("title"),
                    body=item.get("body"),
                    author=item.get("author"),
                    created_at=item.get("created_at"),
                    fetched_at=now,
                    metadata_=item.get("metadata"),
                )
                session.add(post)
                session.flush()
                inserted_this_run += 1
                per_source_new[source_name] = per_source_new.get(source_name, 0) + 1
                if len(new_ids) < _MAX_IDS_IN_STATE:
                    new_ids.append(post.id)
        session.commit()
        return {
            **state,
            "ingested_new_post_ids": new_ids,
            "ingested_new_post_count": inserted_this_run,
            "ingested_new_by_source": per_source_new,
        }
    except Exception as e:
        session.rollback()
        return {**state, "error": str(e)}
    finally:
        session.close()
