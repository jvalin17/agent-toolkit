#!/usr/bin/env python3
"""Tests for hooks/skill_enforce.py — block code edits without active skill."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))


def make_event(file_path):
    return json.dumps({"tool_input": {"file_path": file_path}})


class TestIsCodeFile:
    def test_python_is_code(self):
        from skill_enforce import _is_code_file
        assert _is_code_file("src/app.py") is True

    def test_typescript_is_code(self):
        from skill_enforce import _is_code_file
        assert _is_code_file("src/routes/users.ts") is True

    def test_markdown_is_not_code(self):
        from skill_enforce import _is_code_file
        assert _is_code_file("README.md") is False

    def test_json_is_not_code(self):
        from skill_enforce import _is_code_file
        assert _is_code_file("package.json") is False

    def test_hooks_dir_exempt(self):
        from skill_enforce import _is_code_file
        assert _is_code_file("hooks/session_init.py") is False

    def test_test_files_exempt(self):
        from skill_enforce import _is_code_file
        assert _is_code_file("tests/test_app.py") is False
        assert _is_code_file("src/__tests__/app.test.ts") is False

    def test_scripts_exempt(self):
        from skill_enforce import _is_code_file
        assert _is_code_file("scripts/deploy.py") is False

    def test_docs_exempt(self):
        from skill_enforce import _is_code_file
        assert _is_code_file("docs/guide.py") is False


class TestSkillEnforce:
    def test_allows_non_code_files(self, tmp_path):
        from skill_enforce import run_skill_enforce
        exit_code, output = run_skill_enforce(
            make_event("README.md"), tmp_path
        )
        assert exit_code == 0
        assert output == ""

    def test_allows_test_files(self, tmp_path):
        from skill_enforce import run_skill_enforce
        exit_code, output = run_skill_enforce(
            make_event("tests/test_app.py"), tmp_path
        )
        assert exit_code == 0
        assert output == ""

    def test_warns_on_code_without_skill(self, tmp_path):
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"skill_enforce": "remind"}')
        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        # Should warn (remind mode) but not block
        if output:
            data = json.loads(output)
            assert "additionalContext" in data.get("hookSpecificOutput", {})

    def test_blocks_on_code_without_skill_in_block_mode(self, tmp_path):
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"skill_enforce": "block"}')
        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        if output:
            data = json.loads(output)
            assert data["hookSpecificOutput"].get("permissionDecision") == "deny"

    def test_allows_code_when_skill_active(self, tmp_path):
        from skill_enforce import run_skill_enforce
        # Simulate skill being active
        scratch_dir = tmp_path / ".scratch"
        scratch_dir.mkdir()
        (scratch_dir / "skill_state.json").write_text(
            json.dumps({"last_skill_routed": "build"})
        )
        (tmp_path / "gates.json").write_text('{"skill_enforce": "block"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output == ""

    def test_disabled_when_off(self, tmp_path):
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"skill_enforce": "off"}')
        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output == ""
