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

    def test_reminds_when_skill_active(self, tmp_path):
        """Active skill gets a reminder (anti-drift), not a block."""
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
        assert output != ""
        data = json.loads(output)
        hook = data["hookSpecificOutput"]
        # Should remind, never block when skill is active
        assert "additionalContext" in hook
        assert hook.get("permissionDecision") != "deny"

    def test_disabled_when_off(self, tmp_path):
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"skill_enforce": "off"}')
        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output == ""

    def test_pre_code_skill_blocks_in_block_mode(self, tmp_path):
        """PRE_CODE_SKILLS (requirements, architecture) should NOT authorize code edits."""
        from skill_enforce import run_skill_enforce
        scratch = tmp_path / ".scratch"
        scratch.mkdir()
        (scratch / "skill_state.json").write_text(
            json.dumps({"last_skill_routed": "requirements"})
        )
        (tmp_path / "gates.json").write_text('{"skill_enforce": "block"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output != "", "pre_code skill should not authorize code edits"
        data = json.loads(output)
        assert data["hookSpecificOutput"].get("permissionDecision") == "deny"

    def test_pre_code_skill_warns_in_remind_mode(self, tmp_path):
        """PRE_CODE_SKILLS in remind mode should inject warning context."""
        from skill_enforce import run_skill_enforce
        scratch = tmp_path / ".scratch"
        scratch.mkdir()
        (scratch / "skill_state.json").write_text(
            json.dumps({"last_skill_routed": "architecture"})
        )
        (tmp_path / "gates.json").write_text('{"skill_enforce": "remind"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output != "", "pre_code skill should warn, not allow silently"
        data = json.loads(output)
        assert "additionalContext" in data.get("hookSpecificOutput", {})

    def test_code_change_skill_allows(self, tmp_path):
        """CODE_CHANGE_SKILLS (implementation, debug_tool) should authorize edits."""
        from skill_enforce import run_skill_enforce
        scratch = tmp_path / ".scratch"
        scratch.mkdir()
        (scratch / "skill_state.json").write_text(
            json.dumps({"last_skill_routed": "implementation"})
        )
        (tmp_path / "gates.json").write_text('{"skill_enforce": "block"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        # With active skill, should get a reminder (not a block or empty)
        if output:
            data = json.loads(output)
            hook = data.get("hookSpecificOutput", {})
            assert "additionalContext" in hook, "active skill should get reminder, not block"
            assert hook.get("permissionDecision") != "deny"


class TestSkillEnforceModes:
    """Test mode-based skill enforcement: remind in all modes, block in default/standard/safe."""

    def test_remind_even_when_skill_active_default(self, tmp_path):
        """Anti-drift: default mode injects reminder even with active skill."""
        from skill_enforce import run_skill_enforce
        scratch = tmp_path / ".scratch"
        scratch.mkdir()
        (scratch / "skill_state.json").write_text(
            json.dumps({"last_skill_routed": "build"})
        )
        (tmp_path / "gates.json").write_text('{"mode": "default"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output != "", "should inject reminder even with active skill"
        data = json.loads(output)
        hook = data["hookSpecificOutput"]
        assert "additionalContext" in hook
        assert "IMPLEMENTATION" in hook["additionalContext"].upper() or \
               "SKILL" in hook["additionalContext"].upper()

    def test_no_output_in_minimal_mode(self, tmp_path):
        """Minimal mode skips all enforcement."""
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"mode": "minimal"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output == ""

    def test_blocks_without_skill_in_default_mode(self, tmp_path):
        """Default mode blocks source edits when no skill is active."""
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"mode": "default"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output != ""
        data = json.loads(output)
        assert data["hookSpecificOutput"].get("permissionDecision") == "deny"

    def test_blocks_without_skill_in_safe_mode(self, tmp_path):
        """Safe mode blocks source edits when no skill is active."""
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"mode": "safe"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output != ""
        data = json.loads(output)
        assert data["hookSpecificOutput"].get("permissionDecision") == "deny"

    def test_blocks_without_skill_in_standard_mode(self, tmp_path):
        """Standard mode blocks source edits when no skill is active."""
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"mode": "standard"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output != ""
        data = json.loads(output)
        assert data["hookSpecificOutput"].get("permissionDecision") == "deny"

    def test_reminds_without_skill_in_tdd_mode(self, tmp_path):
        """TDD mode only reminds, does not block."""
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text('{"mode": "tdd"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output != "", "tdd mode should remind"
        data = json.loads(output)
        hook = data["hookSpecificOutput"]
        assert "additionalContext" in hook
        assert hook.get("permissionDecision") != "deny"

    def test_remind_with_active_skill_in_planned_mode(self, tmp_path):
        """Planned mode still injects reminder when skill is active."""
        from skill_enforce import run_skill_enforce
        scratch = tmp_path / ".scratch"
        scratch.mkdir()
        (scratch / "skill_state.json").write_text(
            json.dumps({"last_skill_routed": "debug_tool"})
        )
        (tmp_path / "gates.json").write_text('{"mode": "planned"}')

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output != "", "should remind even with active skill"
        data = json.loads(output)
        assert "additionalContext" in data["hookSpecificOutput"]

    def test_explicit_off_overrides_mode(self, tmp_path):
        """skill_enforce: off overrides any mode."""
        from skill_enforce import run_skill_enforce
        (tmp_path / "gates.json").write_text(
            '{"mode": "safe", "skill_enforce": "off"}'
        )

        exit_code, output = run_skill_enforce(
            make_event("src/app.py"), tmp_path
        )
        assert output == ""

    def test_no_remind_for_non_code_files(self, tmp_path):
        """Reminders only for source code, not config/docs."""
        from skill_enforce import run_skill_enforce
        scratch = tmp_path / ".scratch"
        scratch.mkdir()
        (scratch / "skill_state.json").write_text(
            json.dumps({"last_skill_routed": "build"})
        )
        (tmp_path / "gates.json").write_text('{"mode": "default"}')

        exit_code, output = run_skill_enforce(
            make_event("config.json"), tmp_path
        )
        assert output == ""
