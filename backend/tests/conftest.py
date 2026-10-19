"""Pytest fixtures for backend tests."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import create_app


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client fixture configured against the FastAPI ASGI app."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
