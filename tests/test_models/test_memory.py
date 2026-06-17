"""Tests for the Memory SQLAlchemy model."""

from __future__ import annotations

import pytest

from cptr.models.memory import Memory


@pytest.fixture
def sample_memory_data():
    return {
        "workspace_id": "ws-1",
        "user_id": "user-1",
        "content": "User prefers dark mode in their editor",
        "section": "preferences",
        "tags": ["editor", "theme"],
        "source": "user",
    }


class TestMemoryModel:
    """Tests CRUD operations on the Memory model via its class methods."""

    @pytest.mark.asyncio
    async def test_create_memory(self, db_session, monkeypatch, sample_memory_data):
        _patch_get_db(monkeypatch, db_session)

        memory = await Memory.create(**sample_memory_data, created_at=1000)

        assert memory.id is not None
        assert memory.content == "User prefers dark mode in their editor"
        assert memory.section == "preferences"
        assert memory.tags == ["editor", "theme"]
        assert memory.source == "user"
        assert memory.workspace_id == "ws-1"
        assert memory.user_id == "user-1"
        assert memory.created_at == 1000
        assert memory.updated_at == 1000

    @pytest.mark.asyncio
    async def test_get_by_workspace(self, db_session, monkeypatch, sample_memory_data):
        _patch_get_db(monkeypatch, db_session)
        await Memory.create(**sample_memory_data, created_at=1000)
        await Memory.create(
            workspace_id="ws-1",
            user_id="user-1",
            content="User likes Python",
            section="facts",
            tags=[],
            source="user",
            created_at=2000,
        )
        await Memory.create(
            workspace_id="ws-2",
            user_id="user-1",
            content="Other workspace memory",
            section="general",
            tags=[],
            source="user",
            created_at=3000,
        )

        # Should only get ws-1 memories
        results = await Memory.get_by_workspace("ws-1")
        assert len(results) == 2
        # Ordered newest first
        assert results[0].content == "User likes Python"
        assert results[1].content == "User prefers dark mode in their editor"

    @pytest.mark.asyncio
    async def test_get_by_workspace_with_section(self, db_session, monkeypatch, sample_memory_data):
        _patch_get_db(monkeypatch, db_session)
        await Memory.create(**sample_memory_data, created_at=1000)
        await Memory.create(
            workspace_id="ws-1",
            user_id="user-1",
            content="User knows Python",
            section="facts",
            tags=[],
            source="user",
            created_at=2000,
        )

        results = await Memory.get_by_workspace("ws-1", section="preferences")
        assert len(results) == 1
        assert results[0].section == "preferences"

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session, monkeypatch, sample_memory_data):
        _patch_get_db(monkeypatch, db_session)
        memory = await Memory.create(**sample_memory_data, created_at=1000)

        fetched = await Memory.get_by_id(memory.id)
        assert fetched is not None
        assert fetched.id == memory.id
        assert fetched.content == memory.content

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        fetched = await Memory.get_by_id("nonexistent")
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_memory(self, db_session, monkeypatch, sample_memory_data):
        _patch_get_db(monkeypatch, db_session)
        memory = await Memory.create(**sample_memory_data, created_at=1000)

        deleted = await Memory.delete(memory.id)
        assert deleted is True

        fetched = await Memory.get_by_id(memory.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        deleted = await Memory.delete("nonexistent")
        assert deleted is False

    @pytest.mark.asyncio
    async def test_update_memory(self, db_session, monkeypatch, sample_memory_data):
        _patch_get_db(monkeypatch, db_session)
        memory = await Memory.create(**sample_memory_data, created_at=1000)

        updated = await Memory.update(memory.id, content="Updated content", tags=["updated"])
        assert updated is True

        fetched = await Memory.get_by_id(memory.id)
        assert fetched.content == "Updated content"
        assert fetched.tags == ["updated"]
        # section should remain unchanged
        assert fetched.section == "preferences"
        # updated_at should be newer
        assert fetched.updated_at > 1000

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        updated = await Memory.update("nonexistent", content="new")
        assert updated is False

    @pytest.mark.asyncio
    async def test_search_by_content(self, db_session, monkeypatch, sample_memory_data):
        _patch_get_db(monkeypatch, db_session)
        await Memory.create(**sample_memory_data, created_at=1000)
        await Memory.create(
            workspace_id="ws-1",
            user_id="user-1",
            content="User likes dark chocolate",
            section="preferences",
            tags=[],
            source="user",
            created_at=2000,
        )

        results = await Memory.search_by_content("ws-1", "dark")
        assert len(results) == 2  # both "dark mode" and "dark chocolate"

        results = await Memory.search_by_content("ws-1", "chocolate")
        assert len(results) == 1
        assert results[0].content == "User likes dark chocolate"


def _patch_get_db(monkeypatch, db_session):
    """Patch get_db so model methods use the test engine's session factory.

    db_session is a dict with 'factory' (async_sessionmaker) and 'engine'.
    We patch at the model level because it did ``from cptr.utils.db import get_db``,
    creating a local reference that monkeypatching the source module won't affect.
    """

    async def _fake_get_db():
        return db_session["factory"]()

    monkeypatch.setattr("cptr.models.memory.get_db", _fake_get_db)
