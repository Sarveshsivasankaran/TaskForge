"""Pytest fixtures for backend tests."""

import os
os.environ["APP_ENV"] = "test"
os.environ["SUPABASE_DB_URL"] = "sqlite+aiosqlite:///./taskforge_test.db"

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from app.core.database import init_db, engine


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client fixture configured against the FastAPI ASGI app."""
    await init_db()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    await engine.dispose()
