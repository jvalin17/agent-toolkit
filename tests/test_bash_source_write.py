#!/usr/bin/env python3
"""Tests for Bash source-write detection — invalidates precommit on Bash file edits."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from session_monitor import _detect_bash_source_write  # noqa: E402


class TestBashSourceWriteDetection:
    """Detect Bash commands that write to source files."""

    def test_sed_inplace_detected(self):
        assert _detect_bash_source_write("sed -i 's/old/new/g' src/app.py")

    def test_echo_redirect_detected(self):
        assert _detect_bash_source_write('echo "code" > src/app.py')

    def test_cat_heredoc_redirect_detected(self):
        assert _detect_bash_source_write("cat << 'EOF' > src/handler.ts")

    def test_tee_detected(self):
        assert _detect_bash_source_write("tee src/utils.py")

    def test_cp_to_source_detected(self):
        assert _detect_bash_source_write("cp backup.py src/app.py")

    def test_patch_detected(self):
        assert _detect_bash_source_write("patch < fix.patch")

    def test_mv_to_source_detected(self):
        assert _detect_bash_source_write("mv old.py src/new.py")

    # Non-source writes — should NOT trigger
    def test_echo_without_redirect_ignored(self):
        assert not _detect_bash_source_write('echo "hello world"')

    def test_git_commands_ignored(self):
        assert not _detect_bash_source_write("git commit -m 'feat'")
        assert not _detect_bash_source_write("git push origin main")
        assert not _detect_bash_source_write("git status")

    def test_write_to_markdown_ignored(self):
        assert not _detect_bash_source_write('echo "text" > README.md')

    def test_write_to_json_ignored(self):
        assert not _detect_bash_source_write('echo "{}" > config.json')

    def test_pytest_ignored(self):
        assert not _detect_bash_source_write("python3 -m pytest tests/ -q")

    def test_ls_ignored(self):
        assert not _detect_bash_source_write("ls -la src/")

    def test_cat_read_ignored(self):
        assert not _detect_bash_source_write("cat src/app.py")

    def test_write_to_scratch_ignored(self):
        assert not _detect_bash_source_write('echo "{}" > .scratch/state.json')

    def test_write_to_hooks_ignored(self):
        assert not _detect_bash_source_write("sed -i 's/x/y/' hooks/init.py")


class TestBashPrecommitInvalidation:
    """Bash source writes clear precommit-passed flag."""

    def test_sed_clears_precommit(self, tmp_path):
        gates_dir = tmp_path / ".gates"
        gates_dir.mkdir()
        (gates_dir / "precommit-passed").write_text("READY")
        (tmp_path / "gates.json").write_text('{"mode": "default"}')

        from session_monitor import _invalidate_precommit_on_bash
        _invalidate_precommit_on_bash("sed -i 's/old/new/' src/app.py", tmp_path)
        assert not (gates_dir / "precommit-passed").exists()

    def test_safe_command_keeps_precommit(self, tmp_path):
        gates_dir = tmp_path / ".gates"
        gates_dir.mkdir()
        (gates_dir / "precommit-passed").write_text("READY")
        (tmp_path / "gates.json").write_text('{"mode": "default"}')

        from session_monitor import _invalidate_precommit_on_bash
        _invalidate_precommit_on_bash("python3 -m pytest tests/ -q", tmp_path)
        assert (gates_dir / "precommit-passed").is_file()

    def test_skipped_in_minimal_mode(self, tmp_path):
        gates_dir = tmp_path / ".gates"
        gates_dir.mkdir()
        (gates_dir / "precommit-passed").write_text("READY")
        (tmp_path / "gates.json").write_text('{"mode": "minimal"}')

        from session_monitor import _invalidate_precommit_on_bash
        _invalidate_precommit_on_bash("sed -i 's/old/new/' src/app.py", tmp_path)
        assert (gates_dir / "precommit-passed").is_file()
