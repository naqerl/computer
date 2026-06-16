"""Workspace filesystem helpers."""

from __future__ import annotations

from pathlib import Path


def ensure_cptr_gitignored(workspace: str | Path) -> None:
    """If workspace is a git repo, ensure .cptr is listed in .gitignore."""
    ws = Path(workspace)
    if not (ws / ".git").exists():
        return

    gitignore = ws / ".gitignore"
    entry = ".cptr"

    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped == entry or stripped == entry + "/":
                return
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"{entry}\n"
        gitignore.write_text(content, encoding="utf-8")
    else:
        gitignore.write_text(f"{entry}\n", encoding="utf-8")
