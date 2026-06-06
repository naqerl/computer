"""Reverse proxy to localhost services.

Proxies requests to 127.0.0.1:{port} so that dev servers
started in terminal sessions are accessible from any device.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

# Shared async client, reused across requests
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            follow_redirects=False,
            limits=httpx.Limits(max_connections=20),
        )
    return _client


# Headers we should NOT forward from the upstream
_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}

# Headers we should NOT forward from the client
_SKIP_REQUEST_HEADERS = {
    "host", "connection", "accept-encoding",
}


@router.api_route("/{port}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_request(port: int, path: str, request: Request) -> Response:
    """Proxy a request to localhost:{port}/{path}."""

    if port < 1 or port > 65535:
        return Response(content="Invalid port", status_code=400)

    # Build target URL
    target_url = f"http://127.0.0.1:{port}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    # Forward relevant headers
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in _SKIP_REQUEST_HEADERS:
            headers[key] = value
    headers["host"] = f"127.0.0.1:{port}"

    # Read body for non-GET requests
    body = await request.body() if request.method not in ("GET", "HEAD") else None

    client = _get_client()

    try:
        upstream = await client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=body,
            follow_redirects=False,
        )
    except httpx.ConnectError:
        return Response(
            content=f"Cannot connect to localhost:{port}",
            status_code=502,
            media_type="text/plain",
        )
    except httpx.TimeoutException:
        return Response(
            content=f"Timeout connecting to localhost:{port}",
            status_code=504,
            media_type="text/plain",
        )
    except Exception as e:
        logger.error(f"Proxy error for port {port}: {e}")
        return Response(
            content=f"Proxy error: {e}",
            status_code=502,
            media_type="text/plain",
        )

    # Build response headers, skipping hop-by-hop
    response_headers = {}
    for key, value in upstream.headers.items():
        if key.lower() not in _HOP_BY_HOP:
            response_headers[key] = value

    # Remove X-Frame-Options and CSP frame-ancestors so iframe works
    response_headers.pop("x-frame-options", None)
    response_headers.pop("X-Frame-Options", None)
    csp = response_headers.get("content-security-policy", "")
    if "frame-ancestors" in csp:
        # Remove frame-ancestors directive
        parts = [p.strip() for p in csp.split(";") if "frame-ancestors" not in p]
        if parts:
            response_headers["content-security-policy"] = "; ".join(parts)
        else:
            response_headers.pop("content-security-policy", None)

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
