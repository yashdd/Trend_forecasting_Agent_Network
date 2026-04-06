"""Analyst-grade search (no auth): simple query over topics and raw posts."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import Topic, RawPost, Source

router = APIRouter(prefix="/search")


@router.get("")
async def search(q: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    like = f"%{q}%"
    topics = (
        await db.execute(
            select(Topic).where(or_(Topic.label.ilike(like))).order_by(desc(Topic.updated_at)).limit(limit)
        )
    ).scalars().all()
    posts = (
        await db.execute(
            select(RawPost, Source.name)
            .join(Source, RawPost.source_id == Source.id)
            .where(or_(RawPost.title.ilike(like), RawPost.body.ilike(like)))
            .order_by(desc(RawPost.created_at), desc(RawPost.fetched_at))
            .limit(limit)
        )
    ).all()
    return {
        "query": q,
        "topics": [{"id": t.id, "label": t.label, "category": t.category} for t in topics],
        "posts": [
            {"id": p.id, "source": s, "title": p.title, "url": p.url, "created_at": p.created_at}
            for p, s in posts
        ],
    }

