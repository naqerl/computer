"""Chat router: CRUD for chats + model aggregation."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cptr.models import Chat, ChatMessage, Config
from cptr.utils.config import check_access, now_ms, _get_jwt_secret
from cptr.utils.crypto import decrypt_key

router = APIRouter(prefix="/api/chats", tags=["chats"])

COOKIE_NAME = "cptr_session"


def _get_user(request: Request) -> str:
    """Extract user_id from cookie, raise 401 if not authenticated."""
    token = request.cookies.get(COOKIE_NAME)
    client_host = request.client.host if request.client else "127.0.0.1"
    auth = check_access(client_host=client_host, jwt_token=token)
    if not auth or not auth.user_id:
        raise HTTPException(401, "authentication required")
    return auth.user_id


# ── List chats for a workspace ──────────────────────────────

@router.get("")
async def list_chats(
    request: Request,
    workspace: str = Query(..., description="Workspace root path"),
):
    """List chats for a workspace by scanning .cptr/chats/ for JSON files.

    Returns chat metadata with relative folder paths for sidebar display.
    """
    user_id = _get_user(request)
    chats_dir = Path(workspace) / ".cptr" / "chats"

    if not chats_dir.exists():
        return {"chats": []}

    # Collect chat IDs and their relative folder paths
    chat_entries: list[dict] = []
    for json_file in chats_dir.rglob("*.json"):
        chat_id = json_file.stem
        rel_folder = str(json_file.parent.relative_to(chats_dir))
        if rel_folder == ".":
            rel_folder = ""
        chat_entries.append({"id": chat_id, "folder": rel_folder})

    if not chat_entries:
        return {"chats": []}

    # Batch-fetch from DB
    chat_ids = [e["id"] for e in chat_entries]
    chats = await Chat.get_by_ids(chat_ids)
    chat_map = {c.id: c for c in chats}

    # Build response: only include chats owned by this user
    result = []
    for entry in chat_entries:
        chat = chat_map.get(entry["id"])
        if chat and chat.user_id == user_id:
            result.append({
                "id": chat.id,
                "title": chat.title,
                "summary": chat.summary,
                "folder": entry["folder"],
                "meta": chat.meta,
                "current_message_id": chat.current_message_id,
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
            })

    # Sort: most recently updated first
    result.sort(key=lambda c: c["updated_at"], reverse=True)
    return {"chats": result}

# ── Models aggregation ──────────────────────────────────────
# NOTE: Must be declared before /{chat_id} to avoid 'models' being treated as a chat_id.

async def _get_connections() -> list[dict]:
    return await Config.get("chat.connections") or []


# ── Model cache (app.state) ─────────────────────────────────

async def _get_connection_models(conn: dict, app_state) -> list[str]:
    """Get models for a connection: from stored data, cache, or auto-discover."""
    stored = conn.get("data", {}).get("models")
    if stored:
        return stored

    conn_id = conn.get("id", "")
    cache = getattr(app_state, "MODELS", None)
    if cache is None:
        cache = {}
        app_state.MODELS = cache

    if conn_id in cache:
        return cache[conn_id]

    models = await _fetch_provider_models(conn)
    cache[conn_id] = models
    return models


def invalidate_model_cache(app_state):
    """Clear cached models. Call after connection create/update/delete."""
    app_state.MODELS = {}


@router.get("/models")
async def get_models(request: Request):
    """Aggregate available models across all connections.

    If a connection has data.models set, use those.
    Otherwise, call the provider's /models endpoint to discover available models.
    """
    _get_user(request)
    connections = [c for c in await _get_connections() if c.get("enabled", True)]
    models = []

    for conn in connections:
        model_ids = await _get_connection_models(conn, request.app.state)

        prefix = (conn.get("prefix_id") or "").strip()

        for model_id in (model_ids or []):
            prefixed_id = f"{prefix}/{model_id}" if prefix else model_id
            models.append({
                "id": prefixed_id,
                "name": model_id,
                "provider": conn.get("provider", ""),
                "connection_id": conn["id"],
            })

    default_model = await Config.get("chat.default_model")
    return {"models": models, "default": default_model}


async def _fetch_provider_models(conn: dict) -> list[str]:
    """Discover models from a provider's /models endpoint."""
    import httpx

    secret = _get_jwt_secret()
    api_key = decrypt_key(conn.get("api_key", ""), secret) if conn.get("api_key") else None
    provider = conn.get("provider", "")
    base_url = conn.get("base_url")

    try:
        if provider == "anthropic":
            url = (base_url or "https://api.anthropic.com/v1") + "/models"
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url, headers={
                    "x-api-key": api_key or "",
                    "anthropic-version": "2023-06-01",
                })
                if r.status_code == 200:
                    data = r.json()
                    return [m["id"] for m in data.get("data", [])]

        elif provider == "openai":
            url = (base_url or "https://api.openai.com/v1") + "/models"
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(url, headers={
                    "Authorization": f"Bearer {api_key or ''}",
                })
                if r.status_code == 200:
                    data = r.json()
                    return [m["id"] for m in data.get("data", [])]

    except Exception:
        pass

    return []


# ── Get a chat with all messages ────────────────────────────

@router.get("/{chat_id}")
async def get_chat(chat_id: str, request: Request):
    """Get chat metadata + all messages."""
    user_id = _get_user(request)
    chat = await Chat.get_by_id(chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(404, "chat not found")

    messages = await ChatMessage.get_all_by_chat(chat_id)
    return {
        "chat": {
            "id": chat.id,
            "title": chat.title,
            "summary": chat.summary,
            "meta": chat.meta,
            "current_message_id": chat.current_message_id,
            "created_at": chat.created_at,
            "updated_at": chat.updated_at,
        },
        "messages": [
            _message_dict(m) for m in messages
        ],
    }


def _message_dict(m) -> dict:
    """Serialize a ChatMessage, overlaying live state if task is running."""
    from cptr.utils.chat_task import get_live_state
    d = {
        "id": m.id,
        "parent_id": m.parent_id,
        "role": m.role,
        "content": m.content,
        "model": m.model,
        "done": m.done,
        "output": m.output,
        "usage": m.usage,
        "meta": m.meta,
        "created_at": m.created_at,
    }
    live = get_live_state(m.id)
    if live:
        d["content"] = live["content"]
        d["output"] = live["output"]
        d["done"] = False
    return d


# ── Delete a chat ───────────────────────────────────────────

@router.delete("/{chat_id}")
async def delete_chat(chat_id: str, request: Request):
    """Delete a chat and all its messages."""
    user_id = _get_user(request)
    chat = await Chat.get_by_id(chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(404, "chat not found")

    # Remove .cptr/chats/{id}.json marker
    workspace = chat.meta.get("workspace", "") if chat.meta else ""
    if workspace:
        marker = Path(workspace) / ".cptr" / "chats" / f"{chat_id}.json"
        marker.unlink(missing_ok=True)

    await Chat.delete(chat_id)
    return {"ok": True}


# ── Send a message ──────────────────────────────────────────

class SendMessageRequest(BaseModel):
    content: str = ""
    model_id: str
    workspace: str
    chat_id: Optional[str] = None
    parent_id: Optional[str] = None
    regeneration_prompt: Optional[str] = None
    files: List[str] = []
    params: dict = {}


@router.post("")
async def send_message(body: SendMessageRequest, request: Request):
    """Send a message. Omit chat_id to create a new chat.
    Returns: { chat_id, message_id }
    """
    user_id = _get_user(request)

    # Create or fetch chat
    if body.chat_id:
        chat = await Chat.get_by_id(body.chat_id)
        if not chat or chat.user_id != user_id:
            raise HTTPException(404, "chat not found")
        # Sync params into chat meta
        if chat.meta is None:
            chat.meta = {}
        if chat.meta.get("params") != body.params:
            chat.meta["params"] = body.params
            await Chat.update_meta(chat.id, chat.meta)
    else:
        title = body.content[:50].strip() or "New Chat"
        chat = await Chat.create(
            user_id=user_id,
            title=title,
            meta={"workspace": body.workspace, "params": body.params},
            created_at=now_ms(),
        )
        # Ensure .cptr/chats/ dir exists (export will write the full JSON)
        chats_dir = Path(body.workspace) / ".cptr" / "chats"
        chats_dir.mkdir(parents=True, exist_ok=True)

    # Resolve connection for model
    connection, bare_model = await _resolve_connection(body.model_id, request.app.state)

    # Detect regeneration by checking parent message role
    parent_msg = await ChatMessage.get_by_id(body.parent_id) if body.parent_id else None

    if parent_msg and parent_msg.role == "user":
        # Regeneration: create assistant as sibling of existing response
        assistant_parent = body.parent_id
    else:
        # Normal send: create user message first
        user_msg = await ChatMessage.create(
            chat_id=chat.id,
            role="user",
            content=body.content,
            parent_id=body.parent_id,
            created_at=now_ms(),
        )
        assistant_parent = user_msg.id

    # Create empty assistant message
    assistant_msg = await ChatMessage.create(
        chat_id=chat.id,
        role="assistant",
        content="",
        parent_id=assistant_parent,
        model=body.model_id,
        done=False,
        created_at=now_ms(),
    )

    # Update chat pointer to new leaf
    await Chat.update_current_message(chat.id, assistant_msg.id, now_ms())

    # Start background task (export_chat_to_file runs after task completes)
    from cptr.utils.chat_task import start_task
    start_task(
        message_id=assistant_msg.id,
        chat_id=chat.id,
        user_id=user_id,
        connection=connection,
        workspace=body.workspace,
        model=bare_model,
        regeneration_prompt=body.regeneration_prompt,
    )

    return {"chat_id": chat.id, "message_id": assistant_msg.id}


# ── Approve / reject a pending tool call ────────────────────

class ApproveRequest(BaseModel):
    call_id: str
    approved: bool = True


@router.post("/{chat_id}/messages/{message_id}/approve")
async def approve_tool(
    chat_id: str, message_id: str, body: ApproveRequest, request: Request
):
    """Execute or reject a pending tool call, then continue."""
    user_id = _get_user(request)
    chat = await Chat.get_by_id(chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(404, "chat not found")

    msg = await ChatMessage.get_by_id(message_id)
    if not msg or msg.chat_id != chat_id:
        raise HTTPException(404, "message not found")

    # Find pending tool call
    output = msg.output or []
    call = None
    for item in output:
        if (
            item.get("type") == "function_call"
            and item.get("call_id") == body.call_id
            and item.get("status") == "pending"
        ):
            call = item
            break

    if not call:
        raise HTTPException(400, "no pending tool call with that call_id")

    if body.approved:
        # Execute the tool
        from cptr.utils.tools import execute_tool

        result = await execute_tool(
            call["name"], call.get("arguments", {}), chat.meta.get("workspace", "")
        )
        call["status"] = "completed"
        output.append({
            "type": "function_call_output",
            "call_id": body.call_id,
            "output": result,
        })
        await ChatMessage.update(message_id, output=output, done=False)

        # Resolve connection and continue
        model_id = msg.model or ""
        connection, bare_model = await _resolve_connection(model_id, request.app.state)
        workspace = chat.meta.get("workspace", "") if chat.meta else ""

        from cptr.utils.chat_task import start_task
        start_task(
            message_id=message_id,
            chat_id=chat_id,
            user_id=user_id,
            connection=connection,
            workspace=workspace,
            model=bare_model,
        )
    else:
        call["status"] = "rejected"
        await ChatMessage.update(message_id, output=output, done=True)

    return {"ok": True}


# ── Cancel a running task ───────────────────────────────────

@router.post("/{chat_id}/messages/{message_id}/cancel")
async def cancel_task_endpoint(
    chat_id: str, message_id: str, request: Request
):
    """Cancel running task, preserve partial output."""
    user_id = _get_user(request)
    chat = await Chat.get_by_id(chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(404, "chat not found")

    from cptr.utils.chat_task import cancel_task
    found = await cancel_task(message_id)

    if not found:
        # Task already exited (e.g., waiting for tool approval) but message
        # may still be marked done=False, force-finalize it.
        msg = await ChatMessage.get_by_id(message_id)
        if msg and not msg.done:
            output = msg.output or []
            for item in output:
                if item.get("type") == "function_call" and item.get("status") == "pending":
                    item["status"] = "rejected"
            await ChatMessage.update(message_id, output=output, done=True)

    return {"ok": True}


# ── Update current branch pointer ──────────────────────────

class UpdateCurrentRequest(BaseModel):
    message_id: str


@router.post("/{chat_id}/current")
async def update_current(
    chat_id: str, body: UpdateCurrentRequest, request: Request
):
    """Set current_message_id (the active branch leaf)."""
    user_id = _get_user(request)
    chat = await Chat.get_by_id(chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(404, "chat not found")
    await Chat.update_current_message(chat_id, body.message_id, now_ms())
    return {"ok": True}


# ── Update message content / output ────────────────────────

class UpdateMessageRequest(BaseModel):
    content: Optional[str] = None
    output: Optional[list] = None


@router.patch("/{chat_id}/messages/{message_id}")
async def update_message(
    chat_id: str, message_id: str, body: UpdateMessageRequest, request: Request
):
    """Edit a message's content or output in-place."""
    user_id = _get_user(request)
    chat = await Chat.get_by_id(chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(404, "chat not found")

    updates = {}
    if body.content is not None:
        updates["content"] = body.content
    if body.output is not None:
        updates["output"] = body.output
    if updates:
        await ChatMessage.update(message_id, **updates)
    return {"ok": True}


# ── Create message directly (no task) ──────────────────────

class CreateMessageRequest(BaseModel):
    parent_id: Optional[str] = None
    role: str
    content: str
    output: Optional[list] = None


@router.post("/{chat_id}/messages")
async def create_message_endpoint(
    chat_id: str, body: CreateMessageRequest, request: Request
):
    """Create a message without starting a task (for Save As Copy)."""
    user_id = _get_user(request)
    chat = await Chat.get_by_id(chat_id)
    if not chat or chat.user_id != user_id:
        raise HTTPException(404, "chat not found")

    msg = await ChatMessage.create(
        chat_id=chat_id,
        role=body.role,
        content=body.content,
        parent_id=body.parent_id,
        output=body.output,
        done=True,
        created_at=now_ms(),
    )
    await Chat.update_current_message(chat_id, msg.id, now_ms())
    return {"ok": True, "message_id": msg.id}


async def _resolve_connection(model_id: str, app_state=None) -> tuple[dict, str]:
    """Find connection for model.
    'openrouter/gpt-4o' → connection with prefix_id='openrouter', bare model='gpt-4o'
    'claude-sonnet-4-20250514' → scan all connections for match
    Raises 400 if not found.
    """
    connections = [c for c in await _get_connections() if c.get("enabled", True)]
    if not connections:
        raise HTTPException(400, "no connections configured")

    # Try prefix match first
    if "/" in model_id:
        prefix, bare = model_id.split("/", 1)
        for conn in connections:
            if (conn.get("prefix_id") or "").strip() == prefix:
                return conn, bare

    # Scan all connections using cache
    for conn in connections:
        if app_state:
            model_ids = await _get_connection_models(conn, app_state)
        else:
            model_ids = conn.get("data", {}).get("models") or await _fetch_provider_models(conn)
        prefix = (conn.get("prefix_id") or "").strip()
        for mid in model_ids:
            prefixed = f"{prefix}/{mid}" if prefix else mid
            if prefixed == model_id or mid == model_id:
                return conn, mid

    raise HTTPException(400, f"no connection found for model: {model_id}")
