"""SQLAlchemy async database engine and session setup."""

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
