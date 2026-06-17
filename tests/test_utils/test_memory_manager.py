"""Tests for MemoryManager."""

from __future__ import annotations

import pytest

from cptr.utils.memory.manager import MemoryManager


def _patch_get_db(monkeypatch, db_session):
    """Patch get_db in the models.memory module (where it's imported)."""

    async def _fake_get_db():
        return db_session["factory"]()

    monkeypatch.setattr("cptr.models.memory.get_db", _fake_get_db)


class TestMemoryManager:
    """Tests for MemoryManager read/write operations."""

    @pytest.mark.asyncio
    async def test_add_and_prefetch(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        result = await MemoryManager.add(
            workspace_id="ws-1",
            content="User prefers dark mode",
            section="preferences",
            tags=["editor"],
            source="user",
            user_id="u-1",
        )
        assert result["id"] is not None
        assert result["content"] == "User prefers dark mode"
        assert result["section"] == "preferences"

        # prefetch should return formatted string
        formatted = await MemoryManager.prefetch("ws-1")
        assert "## Saved Knowledge" in formatted
        assert "[preferences] User prefers dark mode" in formatted

    @pytest.mark.asyncio
    async def test_prefetch_empty(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        formatted = await MemoryManager.prefetch("ws-1")
        assert formatted == ""

    @pytest.mark.asyncio
    async def test_prefetch_with_user_filter(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        await MemoryManager.add(
            workspace_id="ws-1", content="Memory 1", section="general", user_id="u-1"
        )
        await MemoryManager.add(
            workspace_id="ws-1", content="Memory 2", section="general", user_id="u-2"
        )

        # Without user filter, both appear
        all_mem = await MemoryManager.prefetch("ws-1")
        assert "Memory 1" in all_mem
        assert "Memory 2" in all_mem

    @pytest.mark.asyncio
    async def test_remove(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        result = await MemoryManager.add(
            workspace_id="ws-1", content="Something", section="general", source="user"
        )
        mid = result["id"]

        ok = await MemoryManager.remove(mid)
        assert ok is True

        ok = await MemoryManager.remove(mid)
        assert ok is False

    @pytest.mark.asyncio
    async def test_replace(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        result = await MemoryManager.add(
            workspace_id="ws-1", content="Original", section="facts", tags=["old"]
        )
        mid = result["id"]

        ok = await MemoryManager.replace(mid, content="Updated", tags=["new"])
        assert ok is True

        # verify via prefetch
        formatted = await MemoryManager.prefetch("ws-1")
        assert "Updated" in formatted
        assert "Original" not in formatted

    @pytest.mark.asyncio
    async def test_replace_nonexistent(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        ok = await MemoryManager.replace("nonexistent", content="new")
        assert ok is False

    @pytest.mark.asyncio
    async def test_search(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        await MemoryManager.add(
            workspace_id="ws-1", content="User likes dark mode", source="user"
        )
        await MemoryManager.add(
            workspace_id="ws-1", content="User likes dark chocolate", source="user"
        )
        await MemoryManager.add(
            workspace_id="ws-1", content="Python is fun", source="user"
        )

        results = await MemoryManager.search("ws-1", "dark")
        assert len(results) == 2

        results = await MemoryManager.search("ws-1", "Python")
        assert len(results) == 1
        assert results[0]["content"] == "Python is fun"

    @pytest.mark.asyncio
    async def test_list_all(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        await MemoryManager.add(
            workspace_id="ws-1", content="First", source="user"
        )
        await MemoryManager.add(
            workspace_id="ws-1", content="Second", source="user"
        )

        mems = await MemoryManager.list_all("ws-1")
        # newest first
        assert len(mems) == 2
        assert mems[0]["content"] == "Second"
        assert mems[1]["content"] == "First"

    @pytest.mark.asyncio
    async def test_list_all_with_section(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)

        await MemoryManager.add(
            workspace_id="ws-1", content="Pref", section="preferences", source="user"
        )
        await MemoryManager.add(
            workspace_id="ws-1", content="Fact", section="facts", source="user"
        )

        mems = await MemoryManager.list_all("ws-1", section="preferences")
        assert len(mems) == 1
        assert mems[0]["section"] == "preferences"
