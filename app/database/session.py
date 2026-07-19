"""Async SQLAlchemy engine + session factory."""
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import get_settings
from app.models.db_models import Base
from app.utils.logger import logger

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.salon_database_url,
        echo=not settings.is_production,
        future=True,
        connect_args={"check_same_thread": False},
    )


async def init_db() -> None:
    """Create tables on startup."""
    global _engine, _session_factory
    _engine = _build_engine()
    _session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialised (SQLite)")


async def close_db() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("Database connection closed")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _session_factory


async def get_db() -> AsyncSession:  # type: ignore[misc]
    """FastAPI dependency that yields an async session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
