"""Tests for the skill_manage tool in tools.py."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cptr.utils.tools import skill_manage


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> str:
    """Create a temporary workspace with .cptr/skills directory."""
    skills_dir = tmp_path / ".cptr" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    return str(tmp_path)


def _make_context(workspace: str):
    return {"workspace": workspace, "user_id": "u-1", "model_id": "test-model"}


SAMPLE_SKILL_CONTENT = """---
name: my-skill
description: A helpful test skill.
---

## Usage
- Use this skill when testing
- It does nothing useful
"""


class TestSkillManageTool:
    """Tests for the ``skill_manage`` tool function.

    Uses a temporary directory as the workspace to avoid touching real files.
    """

    @pytest.mark.asyncio
    async def test_list_empty(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        result = await skill_manage(action="list", __context__=ctx)
        data = json.loads(result)
        assert data["count"] == 0
        assert data["skills"] == []

    @pytest.mark.asyncio
    async def test_create_skill(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        result = await skill_manage(
            action="create",
            name="my-skill",
            content=SAMPLE_SKILL_CONTENT,
            __context__=ctx,
        )
        data = json.loads(result)
        assert data["status"] == "success"
        assert data["name"] == "my-skill"

        # Skill directory should exist with SKILL.md
        skill_dir = Path(tmp_workspace) / ".cptr" / "skills" / "my-skill"
        assert skill_dir.is_dir()
        skill_md = skill_dir / "SKILL.md"
        assert skill_md.exists()
        assert skill_md.read_text().strip() == SAMPLE_SKILL_CONTENT.strip()

    @pytest.mark.asyncio
    async def test_create_duplicate(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        await skill_manage(action="create", name="my-skill",
                           content=SAMPLE_SKILL_CONTENT, __context__=ctx)
        result = await skill_manage(action="create", name="my-skill",
                                    content=SAMPLE_SKILL_CONTENT, __context__=ctx)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_view_skill(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        await skill_manage(action="create", name="my-skill",
                           content=SAMPLE_SKILL_CONTENT, __context__=ctx)
        result = await skill_manage(action="view", name="my-skill", __context__=ctx)
        # format_skill_content wraps in XML, so check key phrases
        assert "my-skill" in result
        assert "Usage" in result

    @pytest.mark.asyncio
    async def test_view_nonexistent(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        result = await skill_manage(action="view", name="no-skill", __context__=ctx)
        data = json.loads(result)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_edit_skill(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)
        new_content = "# my-skill\n\nEdited content\n"

        await skill_manage(action="create", name="my-skill",
                           content=SAMPLE_SKILL_CONTENT, __context__=ctx)
        result = await skill_manage(action="edit", name="my-skill",
                                    content=new_content, __context__=ctx)
        data = json.loads(result)
        assert data["status"] == "success"

        # Verify content changed
        view_result = await skill_manage(action="view", name="my-skill", __context__=ctx)
        assert "Edited content" in view_result

    @pytest.mark.asyncio
    async def test_patch_skill(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        await skill_manage(action="create", name="my-skill",
                           content=SAMPLE_SKILL_CONTENT, __context__=ctx)
        result = await skill_manage(
            action="patch",
            name="my-skill",
            changes=json.dumps({"description": "Updated description"}),
            __context__=ctx,
        )
        data = json.loads(result)
        assert data["status"] == "success"

        # Verify frontmatter was updated by reading SKILL.md directly
        skill_md = Path(tmp_workspace) / ".cptr" / "skills" / "my-skill" / "SKILL.md"
        content = skill_md.read_text()
        assert "Updated description" in content

        # Also verify the skill is still discoverable (description is required)
        list_result = await skill_manage(action="list", __context__=ctx)
        list_data = json.loads(list_result)
        assert list_data["count"] == 1

    @pytest.mark.asyncio
    async def test_archive_skill(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        await skill_manage(action="create", name="my-skill",
                           content=SAMPLE_SKILL_CONTENT, __context__=ctx)
        result = await skill_manage(action="archive", name="my-skill", __context__=ctx)
        data = json.loads(result)
        assert data["status"] == "success"

        # Original dir gone, archived dir exists
        src = Path(tmp_workspace) / ".cptr" / "skills" / "my-skill"
        dst = Path(tmp_workspace) / ".cptr" / "skills" / "archived" / "my-skill"
        assert not src.exists()
        assert dst.is_dir()
        assert (dst / "SKILL.md").exists()

    @pytest.mark.asyncio
    async def test_delete_skill(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        await skill_manage(action="create", name="my-skill",
                           content=SAMPLE_SKILL_CONTENT, __context__=ctx)
        result = await skill_manage(action="delete", name="my-skill", __context__=ctx)
        data = json.loads(result)
        assert data["status"] == "success"

        # Directory should be gone
        skill_dir = Path(tmp_workspace) / ".cptr" / "skills" / "my-skill"
        assert not skill_dir.exists()

    @pytest.mark.asyncio
    async def test_list_after_create(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        await skill_manage(action="create", name="skill-a",
                           content="# skill-a", __context__=ctx)
        await skill_manage(action="create", name="skill-b",
                           content="# skill-b", __context__=ctx)

        result = await skill_manage(action="list", __context__=ctx)
        data = json.loads(result)
        assert data["count"] == 2
        assert "skill-a" in data["skills"]
        assert "skill-b" in data["skills"]

    @pytest.mark.asyncio
    async def test_unknown_action(self, tmp_workspace):
        ctx = _make_context(tmp_workspace)

        result = await skill_manage(action="bogus", __context__=ctx)
        data = json.loads(result)
        assert "error" in data
