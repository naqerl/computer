"""Memory model: persistent knowledge saved by self-study loop or user.

Stores structured memories (preferences, facts, personality traits, etc.)
in SQLite so they're queryable, concurrent-safe, and never lost.
"""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Column, Text, select, delete, or_
from sqlalchemy.dialects.sqlite import JSON

from cptr.models.base import Base
from cptr.utils.db import get_db


def _uuid() -> str:
    return str(uuid.uuid4())


class Memory(Base):
    """A single memory entry associated with a workspace (and optionally a user)."""

    __tablename__ = "memory"

    id = Column(Text, primary_key=True, default=_uuid)
    workspace_id = Column(Text, nullable=False, index=True)
    user_id = Column(Text, nullable=True, index=True)
    content = Column(Text, nullable=False)
    section = Column(Text, nullable=False, server_default="general")
    tags = Column(JSON, nullable=True)  # list[str]
    source = Column(Text, nullable=False, server_default="user")
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=True)

    # ── Class methods ────────────────────────────────────────

    @staticmethod
    async def get_by_workspace(
        workspace_id: str,
        user_id: str | None = None,
        section: str | None = None,
        limit: int = 100,
    ) -> list[Memory]:
        """Fetch memories for a workspace, optionally filtered by user and section.

        Results are ordered newest-first.
        """
        async with await get_db() as db:
            stmt = (
                select(Memory)
                .where(Memory.workspace_id == workspace_id)
                .order_by(Memory.created_at.desc())
                .limit(limit)
            )
            if user_id:
                stmt = stmt.where(Memory.user_id == user_id)
            if section:
                stmt = stmt.where(Memory.section == section)
            result = await db.execute(stmt)
            return list(result.scalars().all())

    @staticmethod
    async def get_by_id(memory_id: str) -> Memory | None:
        async with await get_db() as db:
            return await db.get(Memory, memory_id)

    @staticmethod
    async def create(
        workspace_id: str,
        content: str,
        section: str = "general",
        tags: list[str] | None = None,
        source: str = "user",
        user_id: str | None = None,
        created_at: int | None = None,
    ) -> Memory:
        """Create a new memory entry."""
        import time

        now = created_at or int(time.time() * 1000)
        memory = Memory(
            workspace_id=workspace_id,
            user_id=user_id,
            content=content,
            section=section,
            tags=tags or [],
            source=source,
            created_at=now,
            updated_at=now,
        )
        async with await get_db() as db:
            db.add(memory)
            await db.commit()
            await db.refresh(memory)
            return memory

    @staticmethod
    async def delete(memory_id: str) -> bool:
        """Delete a memory by ID. Returns True if a row was deleted."""
        async with await get_db() as db:
            result = await db.execute(delete(Memory).where(Memory.id == memory_id))
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def update(
        memory_id: str,
        content: str | None = None,
        section: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """Update content, section, and/or tags of a memory."""
        import time

        memory = await Memory.get_by_id(memory_id)
        if not memory:
            return False
        async with await get_db() as db:
            db_memory = await db.get(Memory, memory_id)
            if not db_memory:
                return False
            if content is not None:
                db_memory.content = content
            if section is not None:
                db_memory.section = section
            if tags is not None:
                db_memory.tags = tags
            db_memory.updated_at = int(time.time() * 1000)
            await db.commit()
            return True

    @staticmethod
    async def search_by_content(
        workspace_id: str,
        query: str,
        limit: int = 20,
    ) -> list[Memory]:
        """Simple LIKE search on content within a workspace."""
        async with await get_db() as db:
            stmt = (
                select(Memory)
                .where(Memory.workspace_id == workspace_id)
                .where(Memory.content.ilike(f"%{query}%"))
                .order_by(Memory.created_at.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            return list(result.scalars().all())
