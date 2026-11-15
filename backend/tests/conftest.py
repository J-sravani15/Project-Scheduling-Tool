import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import sys
import os
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.core.config import settings
from app.core.database import get_db


@pytest_asyncio.fixture
async def test_session_factory():
    """Provides a thread-safe / loop-safe session factory with NullPool."""
    test_engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_session_factory):
    """Provides an isolated session for tests using NullPool."""
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_session_factory):
    """Provides an AsyncClient with loop-safe database session dependency override."""
    async def override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
