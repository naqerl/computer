"""Shared fixtures for the test suite.

Uses an in-memory SQLite database so tests are fast and isolated.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from cptr.models.base import Base


@pytest_asyncio.fixture
async def db_session():
    """Create a fresh in-memory SQLite database for each test.

    Creates all tables from the model metadata before yielding the engine
    and session factory, then drops them after the test.
    """
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Return a session factory & engine for use in _patch_get_db
    yield {"factory": factory, "engine": engine}

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def workspace_id() -> str:
    return "test-workspace"


@pytest.fixture
def user_id() -> str:
    return "test-user"
