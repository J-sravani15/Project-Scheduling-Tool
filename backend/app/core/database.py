import logging
from typing import AsyncGenerator, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

logger = logging.getLogger(__name__)

# Base class for all SQLAlchemy declarative models
class Base(DeclarativeBase):
    pass


# Asynchronous SQLAlchemy Engine
engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for obtaining an async database session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_db_connection() -> Dict[str, Any]:
    """
    Safely tests database connectivity without raising unhandled exceptions.
    Returns status and diagnostic details.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            return {
                "connected": True,
                "database": settings.POSTGRES_DB,
                "server": f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}",
                "message": "PostgreSQL connection successful",
            }
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return {
            "connected": False,
            "database": settings.POSTGRES_DB,
            "server": f"{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}",
            "message": "PostgreSQL connection pending credentials or target database setup",
            "error": str(exc),
        }
