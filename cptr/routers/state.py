"""Server-side persistent state for cptr.

Three layers:
  - preferences: global user prefs in user_states table
  - workspaces: per-workspace state in workspaces table (one row per user+path)
  - active workspace: determined by URL query param, not stored server-side
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Request, Query
from cptr.env import DATA_DIR
from cptr.models import UserStates, Workspace
from cptr.utils.config import get_or_create_user

router = APIRouter(prefix="/api/state", tags=["state"])


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


async def _get_user_id(request: Request) -> str | None:
    auth = getattr(request.state, "auth", None)
    if not auth or not auth.username:
        return None
    return await get_or_create_user(auth.username)


# ── Preferences ──────────────────────────────────────────────────

@router.get("/preferences")
async def get_preferences(request: Request):
    """Return global user preferences (theme, locale, etc.)."""
    user_id = await _get_user_id(request)
    if not user_id:
        return {}
    return await UserStates.get_data(user_id)


@router.put("/preferences")
async def put_preferences(request: Request):
    """Save global user preferences."""
    user_id = await _get_user_id(request)
    if not user_id:
        return {"status": "skipped"}
    body = await request.json()
    await UserStates.save_data(user_id, body)
    return {"status": "saved"}


# ── Workspace list ───────────────────────────────────────────────

@router.get("/workspaces")
async def get_workspace_list(request: Request):
    """Return list of all workspace summaries for the sidebar."""
    user_id = await _get_user_id(request)
    if not user_id:
        return []
    workspaces = await Workspace.get_by_user(user_id)
    return [{"path": ws.path, "name": ws.name} for ws in workspaces]


# ── Single workspace CRUD ────────────────────────────────────────

@router.get("/workspace")
async def get_workspace(request: Request, path: str = Query(...)):
    """Return full state for a single workspace."""
    user_id = await _get_user_id(request)
    if not user_id:
        return {}
    ws = await Workspace.get_by_path(user_id, path)
    if not ws:
        return {}
    return {
        "name": ws.name,
        "path": ws.path,
        **ws.data,
    }


@router.put("/workspace")
async def put_workspace(request: Request, path: str = Query(...)):
    """Create or update a single workspace's state."""
    user_id = await _get_user_id(request)
    if not user_id:
        return {"status": "skipped"}
    body = await request.json()
    name = body.pop("name", path.rstrip("/").split("/")[-1] or path)
    # Everything else is workspace data (groups, tabs, etc.)
    await Workspace.upsert(user_id, path, name, body)

    return {"status": "saved"}


@router.delete("/workspace")
async def delete_workspace(request: Request, path: str = Query(...)):
    """Remove a workspace."""
    user_id = await _get_user_id(request)
    if not user_id:
        return {"status": "skipped"}
    await Workspace.delete_by_path(user_id, path)
    return {"status": "deleted"}


# ── Welcome ──────────────────────────────────────────────────────

@router.get("/welcome")
async def get_welcome(request: Request):
    """Return data for the welcome/landing page."""
    import platform
    import socket
    import shutil
    import time
    from importlib.metadata import version as pkg_version

    hostname = socket.gethostname()
    try:
        app_version = pkg_version("cptr")
    except Exception:
        app_version = "dev"

    # System stats
    system = {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count() or 0,
    }

    # Memory (cross-platform)
    try:
        if platform.system() == "Darwin":
            import subprocess
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=2,
            )
            system["memory_total"] = int(result.stdout.strip())
            vm = subprocess.run(
                ["vm_stat"], capture_output=True, text=True, timeout=2,
            )
            pages_free = 0
            page_size = 4096
            for line in vm.stdout.split("\n"):
                if "page size" in line:
                    page_size = int(line.split()[-2])
                if "Pages free" in line:
                    pages_free += int(line.split()[-1].rstrip("."))
                if "Pages inactive" in line:
                    pages_free += int(line.split()[-1].rstrip("."))
            system["memory_available"] = pages_free * page_size
        elif platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                mem = {}
                for line in f:
                    parts = line.split()
                    mem[parts[0].rstrip(":")] = int(parts[1]) * 1024
                system["memory_total"] = mem.get("MemTotal", 0)
                system["memory_available"] = mem.get("MemAvailable", 0)
    except Exception:
        pass

    # Disk
    try:
        disk = shutil.disk_usage(str(Path.home()))
        system["disk_total"] = disk.total
        system["disk_used"] = disk.used
        system["disk_free"] = disk.free
    except Exception:
        pass

    # Uptime
    try:
        if platform.system() == "Darwin":
            import subprocess
            result = subprocess.run(
                ["sysctl", "-n", "kern.boottime"],
                capture_output=True, text=True, timeout=2,
            )
            sec_str = result.stdout.split("sec =")[1].split(",")[0].strip()
            boot_time = int(sec_str)
            system["uptime_seconds"] = int(time.time() - boot_time)
        elif platform.system() == "Linux":
            with open("/proc/uptime") as f:
                system["uptime_seconds"] = int(float(f.read().split()[0]))
    except Exception:
        pass

    # Load average
    try:
        load = os.getloadavg()
        system["load_avg"] = [round(l, 2) for l in load]
    except Exception:
        pass

    # CPU usage
    try:
        import subprocess
        if platform.system() == "Linux":
            with open("/proc/stat") as f:
                line = f.readline()
            parts = line.split()
            idle = int(parts[4])
            total = sum(int(p) for p in parts[1:])
            if total > 0:
                system["cpu_usage"] = round(100.0 * (1.0 - idle / total), 1)
        elif platform.system() == "Darwin":
            load = system.get("load_avg")
            cpus = system.get("cpu_count", 1)
            if load and cpus:
                system["cpu_usage"] = round(min(load[0] / cpus * 100, 100), 1)
    except Exception:
        pass

    # Network interfaces
    try:
        import subprocess
        interfaces = []
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["ifconfig"], capture_output=True, text=True, timeout=2,
            )
            current_iface = ""
            for line in result.stdout.split("\n"):
                if line and not line.startswith("\t") and not line.startswith(" "):
                    current_iface = line.split(":")[0]
                if "inet " in line and "127.0.0.1" not in line:
                    ip = line.strip().split()[1]
                    interfaces.append({"name": current_iface, "ip": ip})
        elif platform.system() == "Linux":
            result = subprocess.run(
                ["ip", "-4", "-o", "addr", "show"],
                capture_output=True, text=True, timeout=2,
            )
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 4 and "127.0.0.1" not in parts[3]:
                    interfaces.append({"name": parts[1], "ip": parts[3].split("/")[0]})
        if interfaces:
            system["network"] = interfaces
    except Exception:
        pass

    # Top processes (by CPU)
    processes = []
    try:
        import subprocess
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["ps", "-Arco", "pid,pcpu,pmem,comm"],
                capture_output=True, text=True, timeout=3,
            )
            for line in result.stdout.strip().split("\n")[1:6]:
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    processes.append({
                        "pid": int(parts[0]),
                        "cpu": float(parts[1]),
                        "mem": float(parts[2]),
                        "name": parts[3],
                    })
        elif platform.system() == "Linux":
            result = subprocess.run(
                ["ps", "-eo", "pid,pcpu,pmem,comm", "--sort=-pcpu", "--no-headers"],
                capture_output=True, text=True, timeout=3,
            )
            for line in result.stdout.strip().split("\n")[:5]:
                parts = line.split(None, 3)
                if len(parts) >= 4:
                    processes.append({
                        "pid": int(parts[0]),
                        "cpu": float(parts[1]),
                        "mem": float(parts[2]),
                        "name": parts[3],
                    })
    except Exception:
        pass

    # Suggested directories
    home = str(Path.home())
    candidates = [
        home,
        str(Path.home() / "Documents"),
        str(Path.home() / "Desktop"),
        str(Path.home() / "Downloads"),
        str(Path.home() / "Projects"),
        str(Path.home() / "projects"),
        str(Path.home() / "code"),
        str(Path.home() / "Code"),
        str(Path.home() / "dev"),
        str(Path.home() / "workspace"),
        str(Path.home() / "src"),
        "/tmp",
    ]
    suggestions = []
    seen = set()
    for c in candidates:
        p = Path(c)
        if p.exists() and p.is_dir() and c not in seen:
            suggestions.append({"name": p.name or c, "path": c})
            seen.add(c)

    # Recent workspaces from DB (most recently used first)
    user_id = await _get_user_id(request)
    recent: list[dict] = []
    if user_id:
        workspaces = await Workspace.get_by_user(user_id)
        # Sort by updated_at descending (most recent first)
        workspaces.sort(key=lambda ws: ws.updated_at or 0, reverse=True)
        recent = [{"name": ws.name, "path": ws.path} for ws in workspaces[:10]]

    return {
        "hostname": hostname,
        "platform": platform.system(),
        "version": app_version,
        "system": system,
        "processes": processes,
        "suggestions": suggestions,
        "recent": recent,
    }
