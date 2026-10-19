"""Database engine, session management, and base declarative class."""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from app.core.logging import logger


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


# Select engine arguments based on driver
engine_kwargs = {"echo": settings.debug}

if "sqlite" in settings.supabase_db_url:
    # SQLite specific concurrency settings
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL pool tuning
    engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    })

engine = create_async_engine(settings.supabase_db_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding transactional database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Creates all database tables defined on Base metadata."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized successfully.")
