"""Chat file export: regenerate .cptr/chats/{id}.json from DB.

The JSON file on disk is the portable backup. DB is the primary store.
This function rebuilds the file from DB state.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from cptr.models import Chat, ChatMessage

logger = logging.getLogger(__name__)


async def export_chat_to_file(chat_id: str) -> None:
    """Regenerate .cptr/chats/{id}.json from the DB."""
    chat = await Chat.get_by_id(chat_id)
    if not chat:
        return

    workspace = (chat.meta or {}).get("workspace", "")
    if not workspace:
        return

    messages = await ChatMessage.get_all_by_chat(chat_id)

    # Build history tree
    msg_map: dict[str, dict] = {}
    for m in messages:
        entry: dict = {
            "id": m.id,
            "parentId": m.parent_id,
            "childrenIds": [],
            "role": m.role,
            "content": m.content or "",
            "timestamp": m.created_at,
        }
        if m.role == "user":
            entry["models"] = [m.model] if m.model else []
        else:
            entry["model"] = m.model
            entry["done"] = m.done
            entry["output"] = m.output or []
            if m.usage:
                entry["usage"] = m.usage

        msg_map[m.id] = entry

    # Wire up childrenIds
    for m in messages:
        if m.parent_id and m.parent_id in msg_map:
            msg_map[m.parent_id]["childrenIds"].append(m.id)

    chat_data = {
        "id": chat.id,
        "title": chat.title,
        "created_at": chat.created_at,
        "updated_at": chat.updated_at,
        "history": {
            "currentId": chat.current_message_id,
            "messages": msg_map,
        },
    }

    chats_dir = Path(workspace) / ".cptr" / "chats"
    chats_dir.mkdir(parents=True, exist_ok=True)
    target = chats_dir / f"{chat_id}.json"

    try:
        target.write_text(json.dumps(chat_data, indent=2, ensure_ascii=False))
    except Exception:
        logger.exception(f"Failed to export chat {chat_id}")
