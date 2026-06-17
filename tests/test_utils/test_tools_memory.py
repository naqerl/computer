"""Tests for the memory tool in tools.py."""

from __future__ import annotations

import json

import pytest

from cptr.utils.tools import memory


def _make_context(workspace="ws-1", user_id="u-1"):
    return {"workspace": workspace, "user_id": user_id, "model_id": "test-model"}


def _patch_get_db(monkeypatch, db_session):
    async def _fake_get_db():
        return db_session["factory"]()

    monkeypatch.setattr("cptr.models.memory.get_db", _fake_get_db)


class TestMemoryTool:
    """Tests for the ``memory`` tool function.

    Each test patches get_db so the underlying MemoryManager uses the
    in-memory test database.
    """

    @pytest.mark.asyncio
    async def test_add_memory(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        result = await memory(action="add", content="User likes dark mode",
                              section="preferences", tags="editor,theme",
                              __context__=ctx)
        data = json.loads(result)
        assert data["status"] == "success"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_add_memory_no_content(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        result = await memory(action="add", content="", __context__=ctx)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_list_memories(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        # Add a couple memories first
        await memory(action="add", content="Memory A", __context__=ctx)
        await memory(action="add", content="Memory B", __context__=ctx)

        result = await memory(action="list", __context__=ctx)
        data = json.loads(result)
        assert data["count"] == 2
        assert len(data["results"]) == 2

    @pytest.mark.asyncio
    async def test_search_memories(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        await memory(action="add", content="User likes dark mode", __context__=ctx)
        await memory(action="add", content="User likes dark chocolate", __context__=ctx)

        result = await memory(action="search", content="dark", __context__=ctx)
        data = json.loads(result)
        assert data["count"] == 2

        result = await memory(action="search", content="chocolate", __context__=ctx)
        data = json.loads(result)
        assert data["count"] == 1

    @pytest.mark.asyncio
    async def test_remove_memory(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        # Add then remove
        add_result = await memory(action="add", content="To delete", __context__=ctx)
        add_data = json.loads(add_result)
        mid = add_data["id"]

        result = await memory(action="remove", memory_id=mid, __context__=ctx)
        data = json.loads(result)
        assert data["status"] == "success"

        # Verify gone
        list_result = await memory(action="list", __context__=ctx)
        list_data = json.loads(list_result)
        assert list_data["count"] == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        result = await memory(action="remove", memory_id="bad-id", __context__=ctx)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_replace_memory(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        add_result = await memory(action="add", content="Original", __context__=ctx)
        add_data = json.loads(add_result)
        mid = add_data["id"]

        result = await memory(action="replace", memory_id=mid, content="Updated",
                              __context__=ctx)
        data = json.loads(result)
        assert data["status"] == "success"

        # Verify via search
        search_result = await memory(action="search", content="Updated", __context__=ctx)
        search_data = json.loads(search_result)
        assert search_data["count"] == 1

    @pytest.mark.asyncio
    async def test_replace_nonexistent(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        result = await memory(action="replace", memory_id="bad-id", content="new",
                              __context__=ctx)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_unknown_action(self, db_session, monkeypatch):
        _patch_get_db(monkeypatch, db_session)
        ctx = _make_context()

        result = await memory(action="bogus", __context__=ctx)
        data = json.loads(result)
        assert "error" in data
