"""Tests for hooks/check_doc_write.sh — blocks writes outside project directory."""

import json
import os
import subprocess
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).parent.parent / "hooks" / "check_doc_write.sh"


def run_hook(file_path: str, cwd: str = None) -> subprocess.CompletedProcess:
    """Run check_doc_write.sh with a Write tool input on stdin."""
    payload = json.dumps({
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": "test"},
    })
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=cwd or os.getcwd(),
        timeout=5,
    )


class TestDocGuardHook:
    """check_doc_write.sh blocks writes outside the project directory."""

    def test_allows_write_inside_project(self, tmp_path):
        """Writes inside CWD are allowed (exit 0, no output)."""
        target = str(tmp_path / "src" / "main.py")
        (tmp_path / "src").mkdir()
        result = run_hook(target, cwd=str(tmp_path))
        assert result.returncode == 0
        # No blocking JSON output
        assert "block" not in result.stdout

    def test_blocks_write_outside_project(self, tmp_path):
        """Writes outside CWD are blocked with JSON decision."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        outside_file = str(tmp_path / "other" / "secret.txt")
        result = run_hook(outside_file, cwd=str(project_dir))
        assert result.returncode == 0  # Hook outputs JSON, doesn't exit non-zero
        output = json.loads(result.stdout)
        assert output["decision"] == "block"
        assert "outside" in output["reason"].lower()

    def test_allows_claude_config_writes(self, tmp_path):
        """Writes to ~/.claude/ are always allowed."""
        home = os.environ.get("HOME", "/tmp")
        target = f"{home}/.claude/memory/test.md"
        result = run_hook(target, cwd=str(tmp_path))
        assert result.returncode == 0
        assert "block" not in result.stdout

    def test_no_path_is_allowed(self, tmp_path):
        """Empty file_path doesn't crash — exits 0."""
        payload = json.dumps({
            "tool_name": "Write",
            "tool_input": {},
        })
        result = subprocess.run(
            ["bash", str(HOOK_PATH)],
            input=payload,
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=5,
        )
        assert result.returncode == 0

    def test_allows_write_in_git_root_from_subdirectory(self, tmp_path):
        """Writes to sibling dirs within git root are allowed (monorepo)."""
        # Set up a real git repo with a subdirectory
        subprocess.run(["git", "init", str(tmp_path)], capture_output=True)
        (tmp_path / "frontend").mkdir()
        (tmp_path / "tests" / "agents").mkdir(parents=True)
        target = str(tmp_path / "tests" / "agents" / "test_thing.py")
        # CWD is the subdirectory, target is sibling — should be allowed
        result = run_hook(target, cwd=str(tmp_path / "frontend"))
        assert result.returncode == 0
        assert "block" not in result.stdout

    def test_blocks_write_outside_git_root(self, tmp_path):
        """Writes outside git root are still blocked even with git detection."""
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", str(repo)], capture_output=True)
        (repo / "frontend").mkdir()
        outside = str(tmp_path / "other" / "file.txt")
        result = run_hook(outside, cwd=str(repo / "frontend"))
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["decision"] == "block"

    def test_block_message_includes_file_path(self, tmp_path):
        """Block reason mentions the offending path for user clarity."""
        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        outside = "/etc/passwd"
        result = run_hook(outside, cwd=str(project_dir))
        output = json.loads(result.stdout)
        assert outside in output["reason"]
