"""SQLAlchemy async database engine and session setup."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

# Lazily initialized references
_engine = None
_async_session = None


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def _get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        
        db_url = settings.database_url
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            
        _engine = create_async_engine(
            db_url,
            echo=False,
            connect_args=connect_args,
        )
    return _engine


def _get_session_maker():
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


# Expose for use by scanner and other direct callers
@property
def async_session():
    return _get_session_maker()


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    session_maker = _get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Create all tables on startup."""
    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def migrate_db():
    """Apply incremental schema migrations for SQLite.

    Uses PRAGMA table_info to check for column existence before issuing
    ALTER TABLE, making each migration fully idempotent and safe to re-run.
    This function is a no-op for non-SQLite backends (Postgres handles
    schema via Alembic or manual migrations).
    """
    import logging
    log = logging.getLogger(__name__)

    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        log.debug("migrate_db: non-SQLite backend, skipping SQLite migrations")
        return

    # Columns to add to paper_trades for the Long-Term weekly indicator snapshot
    new_columns = [
        ("indicator_snapshot_supertrend",      "REAL"),
        ("indicator_snapshot_ema_200",         "REAL"),
        ("indicator_snapshot_weekly_sma_200",  "REAL"),
        ("indicator_snapshot_weekly_rsi",      "REAL"),
        ("indicator_snapshot_weekly_macd",     "REAL"),
        ("indicator_snapshot_weekly_bb_lower", "REAL"),
    ]

    engine = _get_engine()
    async with engine.begin() as conn:
        # Read existing columns in paper_trades
        result = await conn.execute(text("PRAGMA table_info(paper_trades)"))
        existing_cols = {row[1] for row in result.fetchall()}  # row[1] = column name

        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                await conn.execute(
                    text(f"ALTER TABLE paper_trades ADD COLUMN {col_name} {col_type}")
                )
                log.info(f"Migration: added column paper_trades.{col_name}")
            else:
                log.debug(f"Migration: column paper_trades.{col_name} already exists, skipping")
