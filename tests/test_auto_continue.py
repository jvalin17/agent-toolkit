"""Tests for scripts/auto_continue.py — outer session wrapper.

Covers: goal resolution, prompt building, completion detection,
history logging, session dir cleanup, exit reason detection, CLI parsing.
"""

import json
import os
import re
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from scripts.auto_continue import AutoContinue, parse_args


@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def runner(project_dir):
    """Create an AutoContinue instance with defaults."""
    return AutoContinue(
        goal="Build auth system",
        max_budget=None,
        project_dir=project_dir,
        headless=True,
    )


# --- Goal resolution ---


class TestResolveGoal:
    def test_goal_from_arg(self, runner):
        result = runner._resolve_goal()
        assert result == "Build auth system"

    def test_goal_from_handoff(self, project_dir):
        handoff = "# HANDOFF\n\n## Goal\n\nFix the login bug\n\n## Session\n\nNumber: 2\n"
        (project_dir / "HANDOFF.md").write_text(handoff)

        runner = AutoContinue(
            goal=None, max_budget=None, project_dir=project_dir, headless=True
        )
        result = runner._resolve_goal()
        assert "login bug" in result

    def test_goal_arg_overrides_handoff(self, project_dir):
        handoff = "# HANDOFF\n\n## Goal\n\nOld goal\n\n## Session\n\nNumber: 1\n"
        (project_dir / "HANDOFF.md").write_text(handoff)

        runner = AutoContinue(
            goal="New goal", max_budget=None, project_dir=project_dir, headless=True
        )
        result = runner._resolve_goal()
        assert result == "New goal"

    def test_goal_from_prompt_when_no_arg_no_handoff(self, project_dir):
        runner = AutoContinue(
            goal=None, max_budget=None, project_dir=project_dir, headless=True
        )
        with patch("builtins.input", return_value="User typed goal"):
            result = runner._resolve_goal()
        assert result == "User typed goal"


# --- Prompt building ---


class TestBuildPrompt:
    def test_first_session_prompt(self, runner):
        runner.session_count = 1
        prompt = runner._build_prompt()
        assert "HANDOFF.md" in prompt
        assert runner.goal in prompt

    def test_continuation_prompt(self, runner):
        runner.session_count = 3
        prompt = runner._build_prompt()
        assert "HANDOFF.md" in prompt
        assert "continue" in prompt.lower()


# --- Completion detection ---


class TestIsComplete:
    def test_no_handoff_means_complete(self, runner):
        # No HANDOFF.md → agent cleaned up → done
        assert runner._is_complete() is True

    def test_complete_marker_in_handoff(self, runner):
        (runner.handoff_file).write_text("# HANDOFF\n\n## COMPLETE\n\nAll done.\n")
        assert runner._is_complete() is True

    def test_handoff_without_complete_not_done(self, runner):
        (runner.handoff_file).write_text("# HANDOFF\n\n## Next\n\n- More work\n")
        assert runner._is_complete() is False


# --- Seed handoff ---


class TestSeedHandoff:
    def test_creates_handoff_with_goal(self, runner):
        runner._seed_handoff()
        content = runner.handoff_file.read_text()
        assert "## Goal" in content
        assert runner.goal in content
        assert "Session 1" in content

    def test_does_not_overwrite_existing(self, runner):
        runner.handoff_file.write_text("# Existing handoff\n\n## Goal\n\nOld goal\n")
        runner._seed_handoff()
        content = runner.handoff_file.read_text()
        assert "Old goal" in content


# --- Session dir cleanup ---


class TestCleanSessionDir:
    def test_removes_session_dir(self, runner):
        session_dir = runner.project_dir / ".session"
        session_dir.mkdir()
        (session_dir / "state.json").write_text("{}")

        runner._clean_session_dir()
        assert not session_dir.exists()

    def test_no_error_if_missing(self, runner):
        # Should not raise
        runner._clean_session_dir()


# --- Exit reason detection ---


class TestDetectExitReason:
    def test_context_exhaustion_from_state(self, runner):
        session_dir = runner.project_dir / ".session"
        session_dir.mkdir()
        state = {"stopped": 1, "exchanges": 20}
        (session_dir / "state.json").write_text(json.dumps(state))

        reason = runner._detect_exit_reason()
        assert reason == "context_exhaustion"

    def test_context_exhaustion_from_handoff(self, runner):
        runner.handoff_file.write_text("# HANDOFF\n\n## Next\n\n- More work\n")

        reason = runner._detect_exit_reason()
        assert reason == "context_exhaustion"

    def test_unexpected_exit(self, runner):
        # No state file, no handoff
        reason = runner._detect_exit_reason()
        assert reason == "unexpected_exit"


# --- History logging ---


class TestLogHistory:
    def test_appends_to_history_log(self, runner):
        runner.session_count = 1
        runner._log_history("HANDOFF")

        assert runner.history_log.exists()
        content = runner.history_log.read_text()
        assert "Session 1" in content
        assert "HANDOFF" in content

    def test_multiple_entries_appended(self, runner):
        runner.session_count = 1
        runner._log_history("HANDOFF")
        runner.session_count = 2
        runner._log_history("COMPLETE")

        lines = runner.history_log.read_text().strip().split("\n")
        assert len(lines) == 2
        assert "Session 1" in lines[0]
        assert "Session 2" in lines[1]

    def test_includes_timestamp(self, runner):
        runner.session_count = 1
        runner._log_history("HANDOFF")
        content = runner.history_log.read_text()
        # ISO 8601 timestamp: [YYYY-MM-DDTHH:MM:SSZ]
        assert re.search(r"\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\]", content)


# --- Launch session ---


class TestLaunchSession:
    def test_headless_uses_claude_p(self, runner):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            runner._launch_session("test prompt")

        cmd = mock_run.call_args[0][0]
        assert "claude" in cmd
        assert "-p" in cmd
        assert "test prompt" in cmd

    def test_budget_passthrough(self, project_dir):
        runner = AutoContinue(
            goal="Build it",
            max_budget=5.0,
            project_dir=project_dir,
            headless=True,
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            runner._launch_session("test prompt")

        cmd = mock_run.call_args[0][0]
        assert "--max-budget-usd" in cmd
        assert "5.0" in cmd

    def test_interactive_mode_no_p_flag(self, project_dir):
        runner = AutoContinue(
            goal="Build it",
            max_budget=None,
            project_dir=project_dir,
            headless=False,
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            runner._launch_session("test prompt")

        cmd = mock_run.call_args[0][0]
        assert "claude" in cmd
        assert "-p" not in cmd


# --- Main run loop ---


class TestRun:
    def test_completes_on_first_session(self, runner):
        """If session marks COMPLETE in HANDOFF.md → complete."""
        def mock_launch(prompt):
            # Session marks goal as complete
            runner.handoff_file.write_text(
                "# HANDOFF\n\n## COMPLETE\n\nAll done.\n"
            )
            return 0

        with patch.object(runner, "_launch_session", side_effect=mock_launch):
            result = runner.run()

        assert result == 0
        assert runner.session_count == 1

    def test_continues_on_handoff(self, runner):
        """If HANDOFF.md exists after session → continue. Complete on second."""
        call_count = [0]

        def mock_launch(prompt):
            call_count[0] += 1
            if call_count[0] == 1:
                # First session writes HANDOFF
                runner.handoff_file.write_text("# HANDOFF\n\n## Next\n\n- More\n")
            else:
                # Second session completes (removes HANDOFF)
                if runner.handoff_file.exists():
                    runner.handoff_file.unlink()
            return 0

        with patch.object(runner, "_launch_session", side_effect=mock_launch):
            result = runner.run()

        assert result == 0
        assert runner.session_count == 2

    def test_logs_history_each_session(self, runner):
        call_count = [0]

        def mock_launch(prompt):
            call_count[0] += 1
            if call_count[0] == 1:
                runner.handoff_file.write_text("# HANDOFF\n\n## Next\n\n- More\n")
            else:
                if runner.handoff_file.exists():
                    runner.handoff_file.unlink()
            return 0

        with patch.object(runner, "_launch_session", side_effect=mock_launch):
            runner.run()

        content = runner.history_log.read_text()
        assert "HANDOFF" in content
        assert "COMPLETE" in content


# --- CLI parsing ---


class TestParseArgs:
    def test_goal_positional(self):
        args = parse_args(["Build auth system"])
        assert args.goal == "Build auth system"

    def test_headless_flag(self):
        args = parse_args(["--headless", "Build it"])
        assert args.headless is True

    def test_budget_flag(self):
        args = parse_args(["--max-budget-usd", "5.0", "Build it"])
        assert args.max_budget_usd == 5.0

    def test_no_goal(self):
        args = parse_args([])
        assert args.goal is None

    def test_project_dir_default(self):
        args = parse_args([])
        assert args.project_dir == "."
