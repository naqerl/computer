"""MemoryManager: orchestrate memory reads and writes through the Memory model.

This is the public API used by tools (``memory``, ``skill_manage``) and
background review.  It is a stateless wrapper around the ``Memory`` model
class methods — no file I/O, no external providers.
"""

from __future__ import annotations

import logging
from typing import Any

from cptr.models.memory import Memory

logger = logging.getLogger(__name__)


class MemoryManager:
    """Read/write memories via the SQLite-backed Memory model.

    All methods are static / classmethods so they can be used directly
    without instantiating an object (though an instance is fine too).
    """

    # ── Read ──────────────────────────────────────────────────

    @staticmethod
    async def prefetch(
        workspace_id: str,
        user_id: str | None = None,
        max_memories: int = 50,
    ) -> str:
        """Fetch memories for a workspace and format them for system prompt injection.

        Returns an empty string if no memories exist.
        """
        memories = await Memory.get_by_workspace(workspace_id, user_id=user_id, limit=max_memories)
        if not memories:
            return ""

        lines = ["## Saved Knowledge"]
        for m in memories:
            tag_str = f" [{m.section}]" if m.section and m.section != "general" else ""
            lines.append(f"-{tag_str} {m.content}")
        return "\n".join(lines)

    @staticmethod
    async def search(workspace_id: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search memories by content substring. Returns list of dicts."""
        results = await Memory.search_by_content(workspace_id, query, limit=limit)
        return [
            {
                "id": m.id,
                "content": m.content,
                "section": m.section,
                "tags": m.tags or [],
                "source": m.source,
                "created_at": m.created_at,
            }
            for m in results
        ]

    # ── Write ─────────────────────────────────────────────────

    @staticmethod
    async def add(
        workspace_id: str,
        content: str,
        section: str = "general",
        tags: list[str] | None = None,
        source: str = "user",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Add a new memory. Returns the created memory as a dict."""
        memory = await Memory.create(
            workspace_id=workspace_id,
            content=content,
            section=section,
            tags=tags or [],
            source=source,
            user_id=user_id,
        )
        logger.info("[memory] added %s: %s…", memory.id[:8], content[:60])
        return {
            "id": memory.id,
            "content": memory.content,
            "section": memory.section,
            "tags": memory.tags or [],
            "source": memory.source,
            "created_at": memory.created_at,
        }

    @staticmethod
    async def remove(memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if something was deleted."""
        ok = await Memory.delete(memory_id)
        if ok:
            logger.info("[memory] removed %s", memory_id[:8])
        return ok

    @staticmethod
    async def replace(
        memory_id: str,
        content: str | None = None,
        section: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """Update an existing memory. Returns True if it existed."""
        ok = await Memory.update(memory_id, content=content, section=section, tags=tags)
        if ok:
            logger.info("[memory] replaced %s", memory_id[:8])
        return ok

    # ── Listing ───────────────────────────────────────────────

    @staticmethod
    async def list_all(
        workspace_id: str,
        user_id: str | None = None,
        section: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """List all memories for a workspace, newest first."""
        memories = await Memory.get_by_workspace(
            workspace_id, user_id=user_id, section=section, limit=limit
        )
        return [
            {
                "id": m.id,
                "content": m.content,
                "section": m.section,
                "tags": m.tags or [],
                "source": m.source,
                "created_at": m.created_at,
            }
            for m in memories
        ]
