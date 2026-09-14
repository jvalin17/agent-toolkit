"""Tests for hooks/session_log — shared session JSONL discovery."""

import json
from pathlib import Path

import pytest

from hooks.session_log import find_latest_session_log


@pytest.fixture()
def fake_claude_home(tmp_path, monkeypatch):
    """Set up a fake ~/.claude/projects/ tree."""
    projects = tmp_path / ".claude" / "projects"
    projects.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    return projects


def _make_log(project_dir: Path, name: str = "session.jsonl") -> Path:
    log = project_dir / name
    log.write_text(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
    return log


class TestFindLatestSessionLog:
    def test_returns_latest_log(self, fake_claude_home, monkeypatch):
        """Should find the latest .jsonl in the matching project dir."""
        proj = fake_claude_home / "-Users-alice-dev-myproject"
        proj.mkdir()
        _make_log(proj, "old.jsonl")
        latest = _make_log(proj, "new.jsonl")

        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: Path("/Users/alice/dev/myproject")))
        result = find_latest_session_log()
        assert result is not None
        assert result.name == latest.name

    def test_exact_match_no_cross_project(self, fake_claude_home, monkeypatch):
        """Slug '-Users-alice-dev-foo' must NOT match '-Users-alice-dev-foobar'."""
        wrong = fake_claude_home / "-Users-alice-dev-foobar"
        wrong.mkdir()
        _make_log(wrong)

        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: Path("/Users/alice/dev/foo")))
        result = find_latest_session_log()
        assert result is None, "substring matched a different project"

    def test_exact_match_finds_correct(self, fake_claude_home, monkeypatch):
        """Slug '-Users-alice-dev-foo' matches exactly '-Users-alice-dev-foo'."""
        correct = fake_claude_home / "-Users-alice-dev-foo"
        correct.mkdir()
        _make_log(correct)

        wrong = fake_claude_home / "-Users-alice-dev-foobar"
        wrong.mkdir()
        _make_log(wrong)

        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: Path("/Users/alice/dev/foo")))
        result = find_latest_session_log()
        assert result is not None
        assert "-dev-foo" in str(result.parent.name)
        assert "foobar" not in str(result.parent.name)

    def test_missing_log_dir(self, fake_claude_home, monkeypatch):
        """No projects dir entries → None."""
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: Path("/Users/alice/dev/myproject")))
        result = find_latest_session_log()
        assert result is None

    def test_empty_log_dir(self, fake_claude_home, monkeypatch):
        """Project dir exists but no .jsonl files → None."""
        proj = fake_claude_home / "-Users-alice-dev-myproject"
        proj.mkdir()

        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: Path("/Users/alice/dev/myproject")))
        result = find_latest_session_log()
        assert result is None

    def test_no_claude_projects_dir(self, tmp_path, monkeypatch):
        """~/.claude/projects/ doesn't exist → None."""
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        monkeypatch.setattr(Path, "cwd", staticmethod(lambda: Path("/Users/alice/dev/myproject")))
        result = find_latest_session_log()
        assert result is None
