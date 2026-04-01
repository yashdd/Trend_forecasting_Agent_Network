"""Async and sync database session and engine."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import get_settings
from app.db.base import Base

settings = get_settings()

# Sync engine for pipeline jobs (ingestion, etc.)
sync_engine = create_engine(
    settings.database_url_sync,
    echo=settings.debug,
    pool_pre_ping=True,
)
SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine, class_=Session)


def get_sync_session():
    return SyncSessionLocal()


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create tables. Call after pgvector extension is enabled."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync():
    """Create tables using sync engine (e.g. for migrations)."""
    Base.metadata.create_all(bind=sync_engine)
