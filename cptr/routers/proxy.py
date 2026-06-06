"""Reverse proxy to localhost services.

Proxies HTTP requests and WebSocket connections to 127.0.0.1:{port}
so that dev servers started in terminal sessions are accessible
from any device through the cptr UI.

The proxy path cache (shared with proxy_middleware) tracks which
request paths belong to which ports, enabling sub-resource loading
without URL rewriting.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time

import httpx
from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

# ── Shared async HTTP client ────────────────────────────────────

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            follow_redirects=False,
            limits=httpx.Limits(max_connections=50),
        )
    return _client


# ── Path → port cache (used by both proxy router and middleware) ──

# Maps request paths to (port, timestamp).  Populated when requests
# flow through /api/proxy/{port}/... and also by the middleware when
# it proxies sub-resources based on Referer.
proxy_path_cache: dict[str, tuple[int, float]] = {}
CACHE_TTL = 300  # seconds


def cache_path(path: str, port: int) -> None:
    """Associate a request path with a proxy port."""
    proxy_path_cache[path] = (port, time.time())

    # Lazy eviction: prune stale entries when cache gets large
    if len(proxy_path_cache) > 2000:
        now = time.time()
        stale = [k for k, (_, ts) in proxy_path_cache.items() if now - ts > CACHE_TTL]
        for k in stale:
            proxy_path_cache.pop(k, None)


def resolve_cached_port(path: str) -> int | None:
    """Look up a port for a previously-proxied path."""
    entry = proxy_path_cache.get(path)
    if entry is None:
        return None
    port, ts = entry
    if time.time() - ts > CACHE_TTL:
        proxy_path_cache.pop(path, None)
        return None
    return port


# ── Headers ────────────────────────────────────────────────────

_HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}

_SKIP_REQUEST_HEADERS = {
    "host", "connection", "accept-encoding",
}


def _build_request_headers(request: Request, port: int) -> dict[str, str]:
    """Build headers to forward to the upstream server."""
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in _SKIP_REQUEST_HEADERS:
            headers[key] = value
    headers["host"] = f"127.0.0.1:{port}"
    return headers


def _build_response_headers(upstream_headers: httpx.Headers) -> dict[str, str]:
    """Build headers to return to the client, stripping hop-by-hop and frame blockers."""
    headers = {}
    for key, value in upstream_headers.items():
        if key.lower() not in _HOP_BY_HOP:
            headers[key] = value

    # Remove X-Frame-Options so iframe embedding works
    headers.pop("x-frame-options", None)
    headers.pop("X-Frame-Options", None)

    # Remove frame-ancestors from CSP
    csp = headers.get("content-security-policy", "")
    if "frame-ancestors" in csp:
        parts = [p.strip() for p in csp.split(";") if "frame-ancestors" not in p]
        if parts:
            headers["content-security-policy"] = "; ".join(parts)
        else:
            headers.pop("content-security-policy", None)

    # Drop content-length (we might not change the body, but the framework
    # will set it correctly)
    headers.pop("content-length", None)
    headers.pop("Content-Length", None)

    return headers


# ── Core proxy function (reused by middleware) ──────────────────

async def proxy_http_request(port: int, path: str, request: Request) -> Response:
    """Proxy an HTTP request to localhost:{port}/{path}.

    This is the shared implementation used by both the explicit
    /api/proxy/{port}/{path} route and the fallback middleware.
    """
    if port < 1 or port > 65535:
        return Response(content="Invalid port", status_code=400)

    # Build target URL
    target_url = f"http://127.0.0.1:{port}/{path}"
    query = str(request.url.query) if request.url.query else ""
    if query:
        target_url += f"?{query}"

    headers = _build_request_headers(request, port)
    body = await request.body() if request.method not in ("GET", "HEAD") else None
    client = _get_client()

    # Try IPv4, fall back to IPv6
    upstream: httpx.Response | None = None
    for host in ("127.0.0.1", "[::1]"):
        url = target_url if host == "127.0.0.1" else target_url.replace("127.0.0.1", "[::1]")
        try:
            upstream = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                follow_redirects=False,
            )
            break
        except httpx.ConnectError:
            continue
        except httpx.TimeoutException:
            return Response(content=f"Timeout connecting to localhost:{port}", status_code=504, media_type="text/plain")
        except Exception as e:
            logger.error(f"Proxy error for port {port}: {e}")
            return Response(content=f"Proxy error: {e}", status_code=502, media_type="text/plain")

    if upstream is None:
        return Response(content=f"Cannot connect to localhost:{port}", status_code=502, media_type="text/plain")

    response_headers = _build_response_headers(upstream.headers)

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


# ── HTTP proxy route ────────────────────────────────────────────

@router.api_route("/{port}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_route(port: int, path: str, request: Request) -> Response:
    """Proxy an HTTP request to localhost:{port}/{path}."""
    # Cache this path so the middleware can resolve sub-resources
    cache_path(f"/api/proxy/{port}/{path}", port)
    return await proxy_http_request(port, path, request)


# ── WebSocket proxy route ──────────────────────────────────────

@router.websocket("/{port}/ws-proxy")
@router.websocket("/{port}/ws-proxy/{path:path}")
async def proxy_websocket(websocket: WebSocket, port: int, path: str = ""):
    """Proxy a WebSocket connection to localhost:{port}/{path}.

    Used for things like Vite HMR.  Relays frames bidirectionally.
    """
    if port < 1 or port > 65535:
        await websocket.close(code=4000, reason="Invalid port")
        return

    await websocket.accept()

    # Build upstream WS URL -- try IPv6 if IPv4 fails
    query = str(websocket.url.query) if websocket.url.query else ""
    qs = f"?{query}" if query else ""

    upstream_ws = None
    for host in ("127.0.0.1", "[::1]"):
        ws_url = f"ws://{host}:{port}/{path}{qs}"
        try:
            import websockets
            upstream_ws = await asyncio.wait_for(
                websockets.connect(ws_url, additional_headers={"host": f"127.0.0.1:{port}"}),
                timeout=5.0,
            )
            break
        except Exception:
            continue

    if upstream_ws is None:
        await websocket.close(code=4002, reason=f"Cannot connect to localhost:{port}")
        return

    async def client_to_upstream():
        """Relay messages from client WebSocket to upstream."""
        try:
            while True:
                data = await websocket.receive()
                if "text" in data:
                    await upstream_ws.send(data["text"])
                elif "bytes" in data:
                    await upstream_ws.send(data["bytes"])
                else:
                    break
        except (WebSocketDisconnect, Exception):
            pass

    async def upstream_to_client():
        """Relay messages from upstream WebSocket to client."""
        try:
            async for msg in upstream_ws:
                if isinstance(msg, str):
                    await websocket.send_text(msg)
                elif isinstance(msg, bytes):
                    await websocket.send_bytes(msg)
        except Exception:
            pass

    try:
        done, pending = await asyncio.wait(
            [asyncio.create_task(client_to_upstream()), asyncio.create_task(upstream_to_client())],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    finally:
        try:
            await upstream_ws.close()
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
