"""Tests for hooks/session_init.py — SessionStart hook replacement.

Covers: scan_project_files, init_session_state, check_hook_integrity,
detect_continuation, build_context, main (JSON output).
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Import will work after implementation exists
from hooks.session_init import (
    build_context,
    check_hook_integrity,
    clear_stale_gates,
    detect_continuation,
    init_session_state,
    main,
    scan_project_files,
)


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory with common files."""
    return tmp_path


# --- scan_project_files ---


class TestScanProjectFiles:
    def test_priority_files_listed_first(self, project_dir):
        (project_dir / "HANDOFF.md").write_text("# Handoff")
        (project_dir / "project-state.md").write_text("# State")
        (project_dir / "random.md").write_text("# Random")

        files, _ = scan_project_files(project_dir)
        # Priority files should appear before non-priority
        priority_entries = [e for e in files if "PRIORITY" in e]
        assert len(priority_entries) == 2
        assert "HANDOFF.md" in priority_entries[0]
        assert "project-state.md" in priority_entries[1]

    def test_requirements_and_architecture_dirs(self, project_dir):
        req_dir = project_dir / "requirements"
        req_dir.mkdir()
        (req_dir / "auth.md").write_text("# Auth")
        arch_dir = project_dir / "architecture"
        arch_dir.mkdir()
        (arch_dir / "system.md").write_text("# System")

        files, _ = scan_project_files(project_dir)
        assert any("requirements/auth.md" in e for e in files)
        assert any("architecture/system.md" in e for e in files)

    def test_reports_counted_not_listed(self, project_dir):
        reports_dir = project_dir / "reports" / "evaluate"
        reports_dir.mkdir(parents=True)
        (reports_dir / "report1.md").write_text("# R1")
        (reports_dir / "report2.md").write_text("# R2")

        files, report_count = scan_project_files(project_dir)
        # Reports should be counted but not individually listed
        assert report_count == 2
        assert not any("report1.md" in e for e in files)

    def test_readme_excluded(self, project_dir):
        (project_dir / "README.md").write_text("# README")
        (project_dir / "proposal.md").write_text("# Proposal")

        result_files, _ = scan_project_files(project_dir)
        assert not any("README.md" in e for e in result_files)
        assert any("proposal.md" in e for e in result_files)

    def test_empty_directory(self, project_dir):
        result_files, report_count = scan_project_files(project_dir)
        assert result_files == []
        assert report_count == 0

    def test_claude_md_is_priority(self, project_dir):
        (project_dir / "CLAUDE.md").write_text("# Claude")

        result_files, _ = scan_project_files(project_dir)
        priority = [e for e in result_files if "PRIORITY" in e]
        assert any("CLAUDE.md" in e for e in priority)

    def test_decisions_md_is_priority(self, project_dir):
        (project_dir / "DECISIONS.md").write_text("# Decisions")

        result_files, _ = scan_project_files(project_dir)
        priority = [e for e in result_files if "PRIORITY" in e]
        assert any("DECISIONS.md" in e for e in priority)


# --- init_session_state ---


class TestInitSessionState:
    def test_creates_state_json(self, project_dir):
        session_dir = project_dir / ".session"
        state = init_session_state(session_dir)

        state_file = session_dir / "state.json"
        assert state_file.exists()

        data = json.loads(state_file.read_text())
        assert data["exchanges"] == 0
        assert data["tool_calls"] == 0
        assert data["cumulative_output_bytes"] == 0
        assert data["compactions"] == 0
        assert data["warned"] is False
        assert data["stopped"] == 0
        assert data["stop_at_tool_call"] == 0
        assert "session_start" in data

    def test_creates_session_directory(self, project_dir):
        session_dir = project_dir / ".session"
        assert not session_dir.exists()

        init_session_state(session_dir)
        assert session_dir.is_dir()

    def test_overwrites_existing_state(self, project_dir):
        session_dir = project_dir / ".session"
        session_dir.mkdir()
        (session_dir / "state.json").write_text('{"exchanges": 99}')

        init_session_state(session_dir)
        data = json.loads((session_dir / "state.json").read_text())
        assert data["exchanges"] == 0


# --- check_hook_integrity ---


class TestCheckHookIntegrity:
    def test_no_warnings_when_all_present(self, project_dir):
        hooks_dir = project_dir / "hooks"
        hooks_dir.mkdir()
        required = [
            "gate.sh", "skill-passed.sh", "gate-cleanup.sh",
            "route-to-skill.sh", "session-init.sh", "session-monitor.sh",
            "tdd-enforce.sh",
        ]
        for hook in required:
            hook_file = hooks_dir / hook
            hook_file.write_text("#!/bin/bash")
            hook_file.chmod(0o755)

        warnings = check_hook_integrity(hooks_dir, settings_path=None)
        assert warnings == []

    def test_missing_hook_reported(self, project_dir):
        hooks_dir = project_dir / "hooks"
        hooks_dir.mkdir()
        # Only create some hooks
        (hooks_dir / "gate.sh").write_text("#!/bin/bash")
        (hooks_dir / "gate.sh").chmod(0o755)

        warnings = check_hook_integrity(hooks_dir, settings_path=None)
        assert any("MISSING" in w for w in warnings)

    def test_non_executable_hook_reported(self, project_dir):
        hooks_dir = project_dir / "hooks"
        hooks_dir.mkdir()
        required = [
            "gate.sh", "skill-passed.sh", "gate-cleanup.sh",
            "route-to-skill.sh", "session-init.sh", "session-monitor.sh",
            "tdd-enforce.sh",
        ]
        for hook in required:
            hook_file = hooks_dir / hook
            hook_file.write_text("#!/bin/bash")
            if hook == "gate.sh":
                hook_file.chmod(0o644)  # Not executable
            else:
                hook_file.chmod(0o755)

        warnings = check_hook_integrity(hooks_dir, settings_path=None)
        assert any("NOT EXECUTABLE" in w and "gate.sh" in w for w in warnings)

    def test_settings_missing_hook_registration(self, project_dir):
        hooks_dir = project_dir / "hooks"
        hooks_dir.mkdir()
        required = [
            "gate.sh", "skill-passed.sh", "gate-cleanup.sh",
            "route-to-skill.sh", "session-init.sh", "session-monitor.sh",
            "tdd-enforce.sh",
        ]
        for hook in required:
            hook_file = hooks_dir / hook
            hook_file.write_text("#!/bin/bash")
            hook_file.chmod(0o755)

        settings_file = project_dir / "settings.json"
        settings_file.write_text(json.dumps({"hooks": {}}))

        warnings = check_hook_integrity(hooks_dir, settings_path=settings_file)
        assert any("NOT REGISTERED" in w for w in warnings)

    def test_settings_with_hooks_registered(self, project_dir):
        hooks_dir = project_dir / "hooks"
        hooks_dir.mkdir()
        required = [
            "gate.sh", "skill-passed.sh", "gate-cleanup.sh",
            "route-to-skill.sh", "session-init.sh", "session-monitor.sh",
            "tdd-enforce.sh",
        ]
        for hook in required:
            hook_file = hooks_dir / hook
            hook_file.write_text("#!/bin/bash")
            hook_file.chmod(0o755)

        settings_content = json.dumps({
            "hooks": {
                "PreToolUse": [
                    {"hooks": [{"command": "gate.sh"}]},
                    {"hooks": [{"command": "session-monitor.sh"}]},
                ],
                "PostToolUse": [
                    {"hooks": [{"command": "skill-passed.sh"}]},
                ],
            }
        })
        settings_file = project_dir / "settings.json"
        settings_file.write_text(settings_content)

        warnings = check_hook_integrity(hooks_dir, settings_path=settings_file)
        # All three checked hooks should be found
        registration_warnings = [w for w in warnings if "NOT REGISTERED" in w]
        assert registration_warnings == []


# --- detect_continuation ---


class TestDetectContinuation:
    def test_no_handoff_file(self, project_dir):
        is_continuation, goal, session_number = detect_continuation(project_dir)
        assert is_continuation is False
        assert goal == ""
        assert session_number == 0

    def test_handoff_with_goal(self, project_dir):
        handoff = """# HANDOFF

## Goal

Build auth system with token refresh

## Session

Number: 3
Previous sessions: 2

## Done

- [x] Token storage
"""
        (project_dir / "HANDOFF.md").write_text(handoff)

        is_continuation, goal, session_number = detect_continuation(project_dir)
        assert is_continuation is True
        assert "auth system" in goal
        assert session_number == 3

    def test_handoff_without_goal_section(self, project_dir):
        handoff = """# HANDOFF

## Done

- [x] Something
"""
        (project_dir / "HANDOFF.md").write_text(handoff)

        is_continuation, goal, session_number = detect_continuation(project_dir)
        assert is_continuation is True
        assert goal == ""
        assert session_number == 0

    def test_handoff_with_complete_marker(self, project_dir):
        handoff = """# HANDOFF

## COMPLETE

All tasks done.
"""
        (project_dir / "HANDOFF.md").write_text(handoff)

        is_continuation, goal, session_number = detect_continuation(project_dir)
        # COMPLETE marker means nothing to continue
        assert is_continuation is False

    def test_session_number_parsing(self, project_dir):
        handoff = """# HANDOFF

## Goal

Fix bugs

## Session

Number: 7
Previous sessions: 6
"""
        (project_dir / "HANDOFF.md").write_text(handoff)

        _, _, session_number = detect_continuation(project_dir)
        assert session_number == 7


# --- build_context ---


class TestBuildContext:
    def test_includes_mandatory_rules(self):
        context = build_context(
            files=["- HANDOFF.md (PRIORITY — read this first)"],
            report_count=0,
            warnings=[],
            continuation=None,
        )
        assert "MANDATORY RULES" in context
        assert "AGENT TOOLKIT ACTIVE" in context
        assert "G-SESSION-1" in context

    def test_includes_file_list(self):
        files = [
            "- HANDOFF.md (PRIORITY — read this first)",
            "- requirements/auth.md",
        ]
        context = build_context(files=files, report_count=0, warnings=[], continuation=None)
        assert "HANDOFF.md" in context
        assert "requirements/auth.md" in context

    def test_includes_report_count(self):
        context = build_context(
            files=["- HANDOFF.md (PRIORITY — read this first)"],
            report_count=5,
            warnings=[],
            continuation=None,
        )
        assert "5 report(s)" in context

    def test_includes_warnings(self):
        warnings = ["MISSING hook: gate.sh", "NOT EXECUTABLE: tdd-enforce.sh"]
        context = build_context(files=[], report_count=0, warnings=warnings, continuation=None)
        assert "HARNESS INTEGRITY WARNINGS" in context
        assert "MISSING hook: gate.sh" in context

    def test_includes_continuation_context(self):
        continuation = {
            "goal": "Build auth system",
            "session_number": 3,
        }
        context = build_context(
            files=["- HANDOFF.md (PRIORITY — read this first)"],
            report_count=0,
            warnings=[],
            continuation=continuation,
        )
        assert "CONTINUATION SESSION" in context
        assert "session 3" in context.lower() or "Session 3" in context
        assert "Build auth system" in context

    def test_no_files_message(self):
        context = build_context(files=[], report_count=0, warnings=[], continuation=None)
        assert "No project .md files found" in context

    def test_available_skills_listed(self):
        context = build_context(files=[], report_count=0, warnings=[], continuation=None)
        assert "/requirements" in context
        assert "/precommit" in context


# --- clear_stale_gates ---


class TestClearStaleGates:
    def test_clears_gate_files(self, project_dir):
        gates_dir = project_dir / ".gates"
        gates_dir.mkdir()
        (gates_dir / "impl.gate").write_text("locked")
        (gates_dir / "debug.gate").write_text("locked")

        warnings = clear_stale_gates(project_dir)
        assert not gates_dir.exists() or len(list(gates_dir.iterdir())) == 0
        assert any("2 files" in w for w in warnings)

    def test_no_gates_dir(self, project_dir):
        warnings = clear_stale_gates(project_dir)
        assert warnings == []

    def test_empty_gates_dir(self, project_dir):
        gates_dir = project_dir / ".gates"
        gates_dir.mkdir()

        warnings = clear_stale_gates(project_dir)
        assert warnings == []


# --- main (JSON output) ---


class TestMain:
    def test_outputs_valid_json(self, project_dir):
        """main() should output valid SessionStart JSON."""
        with patch("hooks.session_init.get_project_dir", return_value=project_dir):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps({
                    "hook_event_name": "SessionStart",
                })
                with patch("sys.stdout") as mock_stdout:
                    written = []
                    mock_stdout.write = lambda s: written.append(s)
                    mock_stdout.flush = lambda: None

                    with patch("hooks.session_init.get_settings_path", return_value=None):
                        exit_code = main()

        assert exit_code == 0
        output = "".join(written)
        data = json.loads(output)
        assert "hookSpecificOutput" in data
        assert data["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in data["hookSpecificOutput"]

    def test_initializes_state_file(self, project_dir):
        """main() should create .session/state.json."""
        with patch("hooks.session_init.get_project_dir", return_value=project_dir):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps({
                    "hook_event_name": "SessionStart",
                })
                with patch("sys.stdout") as mock_stdout:
                    mock_stdout.write = lambda s: None
                    mock_stdout.flush = lambda: None

                    with patch("hooks.session_init.get_settings_path", return_value=None):
                        main()

        state_file = project_dir / ".session" / "state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["exchanges"] == 0

    def test_continuation_context_injected(self, project_dir):
        """When HANDOFF.md exists with a goal, continuation context appears."""
        handoff = "# HANDOFF\n\n## Goal\n\nBuild the widget\n\n## Session\n\nNumber: 2\n"
        (project_dir / "HANDOFF.md").write_text(handoff)

        with patch("hooks.session_init.get_project_dir", return_value=project_dir):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = json.dumps({
                    "hook_event_name": "SessionStart",
                })
                with patch("sys.stdout") as mock_stdout:
                    written = []
                    mock_stdout.write = lambda s: written.append(s)
                    mock_stdout.flush = lambda: None

                    with patch("hooks.session_init.get_settings_path", return_value=None):
                        main()

        output = "".join(written)
        data = json.loads(output)
        context = data["hookSpecificOutput"]["additionalContext"]
        assert "CONTINUATION SESSION" in context
        assert "Build the widget" in context
