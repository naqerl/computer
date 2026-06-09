"""Chat and ChatMessage models with data-access class methods."""

from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Text, select, update, delete
from sqlalchemy.dialects.sqlite import JSON

from cptr.models.base import Base
from cptr.utils.db import get_db


def _uuid() -> str:
    return str(uuid.uuid4())


class Chat(Base):
    """A chat conversation. Workspace association lives in the filesystem."""

    __tablename__ = "chats"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    current_message_id = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)  # {model_id, connection_id, pinned, archived, ...}
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    # ── Class methods ────────────────────────────────────────

    @staticmethod
    async def get_by_id(chat_id: str) -> Chat | None:
        async with await get_db() as db:
            result = await db.execute(select(Chat).where(Chat.id == chat_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def get_by_ids(chat_ids: list[str]) -> list[Chat]:
        """Batch-fetch chats by a list of IDs."""
        if not chat_ids:
            return []
        async with await get_db() as db:
            result = await db.execute(select(Chat).where(Chat.id.in_(chat_ids)))
            return list(result.scalars().all())

    @staticmethod
    async def create(
        user_id: str,
        title: str,
        meta: dict | None = None,
        created_at: int = 0,
    ) -> Chat:
        async with await get_db() as db:
            chat = Chat(
                user_id=user_id,
                title=title,
                meta=meta,
                created_at=created_at,
                updated_at=created_at,
            )
            db.add(chat)
            await db.commit()
            await db.refresh(chat)
            return chat

    @staticmethod
    async def update_title(chat_id: str, title: str, updated_at: int = 0) -> bool:
        async with await get_db() as db:
            result = await db.execute(
                update(Chat).where(Chat.id == chat_id).values(title=title, updated_at=updated_at)
            )
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def update_summary(chat_id: str, summary: str, updated_at: int = 0) -> bool:
        async with await get_db() as db:
            result = await db.execute(
                update(Chat)
                .where(Chat.id == chat_id)
                .values(summary=summary, updated_at=updated_at)
            )
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def update_meta(chat_id: str, meta: dict, updated_at: int = 0) -> bool:
        async with await get_db() as db:
            result = await db.execute(
                update(Chat).where(Chat.id == chat_id).values(meta=meta, updated_at=updated_at)
            )
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def update_current_message(
        chat_id: str, message_id: str | None, updated_at: int = 0
    ) -> bool:
        async with await get_db() as db:
            result = await db.execute(
                update(Chat)
                .where(Chat.id == chat_id)
                .values(current_message_id=message_id, updated_at=updated_at)
            )
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def delete(chat_id: str) -> bool:
        async with await get_db() as db:
            # Messages cascade via FK, but be explicit
            await db.execute(delete(ChatMessage).where(ChatMessage.chat_id == chat_id))
            result = await db.execute(delete(Chat).where(Chat.id == chat_id))
            await db.commit()
            return result.rowcount > 0


class ChatMessage(Base):
    """A single message in a chat conversation."""

    __tablename__ = "chat_messages"

    id = Column(Text, primary_key=True, default=_uuid)
    chat_id = Column(Text, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Text, nullable=True)
    role = Column(Text, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)  # Flattened text content
    model = Column(Text, nullable=True)  # Model used (assistant only)
    done = Column(Boolean, default=True)  # false = streaming or pending approval
    output = Column(JSON, nullable=True)  # Responses API output items
    usage = Column(JSON, nullable=True)  # {input_tokens, output_tokens, ...}
    meta = Column(JSON, nullable=True)  # {files, followups, error, ...}
    created_at = Column(BigInteger, nullable=False)

    # ── Class methods ────────────────────────────────────────

    @staticmethod
    async def get_by_id(message_id: str) -> ChatMessage | None:
        async with await get_db() as db:
            result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
            return result.scalar_one_or_none()

    @staticmethod
    async def get_all_by_chat(chat_id: str) -> list[ChatMessage]:
        """Get all messages for a chat, ordered by creation time."""
        async with await get_db() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.chat_id == chat_id)
                .order_by(ChatMessage.created_at)
            )
            return list(result.scalars().all())

    @staticmethod
    async def get_children(parent_id: str) -> list[ChatMessage]:
        """Get child messages (for branching conversations)."""
        async with await get_db() as db:
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.parent_id == parent_id)
                .order_by(ChatMessage.created_at)
            )
            return list(result.scalars().all())

    @staticmethod
    async def create(
        chat_id: str,
        role: str,
        content: str,
        parent_id: str | None = None,
        model: str | None = None,
        done: bool = True,
        output: dict | list | None = None,
        usage: dict | None = None,
        meta: dict | None = None,
        created_at: int = 0,
    ) -> ChatMessage:
        async with await get_db() as db:
            msg = ChatMessage(
                chat_id=chat_id,
                parent_id=parent_id,
                role=role,
                content=content,
                model=model,
                done=done,
                output=output,
                usage=usage,
                meta=meta,
                created_at=created_at,
            )
            db.add(msg)
            await db.commit()
            await db.refresh(msg)
            return msg

    @staticmethod
    async def update(message_id: str, **kwargs) -> bool:
        """Update arbitrary fields on a message."""
        if not kwargs:
            return False
        async with await get_db() as db:
            result = await db.execute(
                update(ChatMessage).where(ChatMessage.id == message_id).values(**kwargs)
            )
            await db.commit()
            return result.rowcount > 0

    @staticmethod
    async def delete(message_id: str) -> bool:
        async with await get_db() as db:
            result = await db.execute(delete(ChatMessage).where(ChatMessage.id == message_id))
            await db.commit()
            return result.rowcount > 0
