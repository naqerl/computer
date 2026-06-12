"""Audio router: STT transcription via Whisper-compatible API."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, Request, UploadFile

from cptr.models import Config
from cptr.utils.config import _get_jwt_secret, check_access
from cptr.utils.crypto import decrypt_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audio", tags=["audio"])

COOKIE_NAME = "cptr_session"


def _get_user(request: Request) -> str:
    """Extract user_id from cookie, raise 401 if not authenticated."""
    token = request.cookies.get(COOKIE_NAME)
    client_host = request.client.host if request.client else "127.0.0.1"
    auth = check_access(client_host=client_host, jwt_token=token)
    if not auth or not auth.user_id:
        raise HTTPException(401, "authentication required")
    return auth.user_id


@router.post("/transcribe")
async def transcribe(file: UploadFile, request: Request):
    """Send audio to a Whisper-compatible STT API, return transcript text.

    Reads credentials from audio.stt_* config keys (set in Admin → Audio).
    """
    _get_user(request)

    api_key_encrypted = await Config.get("audio.stt_api_key")
    if not api_key_encrypted:
        raise HTTPException(
            400,
            "Speech-to-text not configured. Set up in Settings → Audio.",
        )

    api_key = decrypt_key(api_key_encrypted, _get_jwt_secret())
    base_url = (await Config.get("audio.stt_base_url")) or "https://api.openai.com/v1"
    model = (await Config.get("audio.stt_model")) or "whisper-1"

    data = await file.read()
    filename = file.filename or "audio.webm"
    content_type = file.content_type or "audio/webm"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60)) as client:
            resp = await client.post(
                f"{base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, data, content_type)},
                data={"model": model},
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "[transcribe] STT API error %s: %s",
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise HTTPException(502, f"STT API error: {exc.response.status_code}")
    except httpx.ConnectError:
        raise HTTPException(502, "Could not connect to STT API")

    return {"text": resp.json().get("text", "")}
