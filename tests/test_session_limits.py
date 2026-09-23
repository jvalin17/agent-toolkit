"""Tests for hooks/session_limits.py — two-layer session limit enforcement."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))

from session_limits import (
    _write_breadcrumb_handoff,
    _write_final_handoff,
    apply_session_limits,
    RESTART_PROMPT_TEMPLATE,
)
from session_state import SessionState


@pytest.fixture()
def state():
    return SessionState(
        session_start=0,
        exchanges=10,
        cumulative_output_bytes=1000,
        warned=False,
        stopped=0,
    )


@pytest.fixture()
def tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestWriteBreadcrumbHandoff:
    def test_creates_handoff_file(self, tmp_cwd, state):
        with patch("session_limits.write_auto_handoff") as mock_write, \
             patch("session_limits.get_git_log", return_value="log"):
            _write_breadcrumb_handoff(state, "compact threshold")
            mock_write.assert_called_once()
            call_kwargs = mock_write.call_args
            assert "[BREADCRUMB]" in call_kwargs[1]["stop_reason"]

    def test_reads_existing_handoff(self, tmp_cwd, state):
        handoff = tmp_cwd / "HANDOFF.md"
        handoff.write_text("# Previous content")
        with patch("session_limits.write_auto_handoff") as mock_write, \
             patch("session_limits.get_git_log", return_value="log"):
            _write_breadcrumb_handoff(state, "compact threshold")
            call_kwargs = mock_write.call_args
            assert call_kwargs[1]["previous_handoff"] == "# Previous content"


class TestWriteFinalHandoff:
    def test_appends_restart_prompt(self, tmp_cwd, state):
        with patch("session_limits.write_auto_handoff") as mock_write, \
             patch("session_limits.get_git_log", return_value="log"):
            # write_auto_handoff writes the file, so we need to create it
            def side_effect(**kwargs):
                kwargs["handoff_path"].write_text("# Handoff content\n")
            mock_write.side_effect = side_effect

            _write_final_handoff(state, "time limit")
            content = (tmp_cwd / "HANDOFF.md").read_text()
            assert "Restart Prompt" in content
            assert "[HARD STOP]" in mock_write.call_args[1]["stop_reason"]


class TestApplySessionLimits:
    def test_hard_stop_returns_message(self, tmp_cwd, state):
        with patch("session_limits.check_thresholds", return_value=(True, "200 min")), \
             patch("session_limits._write_final_handoff"):
            new_state, msg = apply_session_limits(state)
            assert "HARD STOP" in msg
            assert new_state.stopped == 2

    def test_hard_stop_only_fires_once(self, tmp_cwd, state):
        state.stopped = 2  # already stopped
        with patch("session_limits.check_thresholds", return_value=(True, "200 min")), \
             patch("session_limits.check_compact_threshold", return_value=(False, "")):
            _, msg = apply_session_limits(state)
            assert msg == ""

    def test_compact_threshold_returns_checkpoint(self, tmp_cwd, state):
        with patch("session_limits.check_thresholds", return_value=(False, "")), \
             patch("session_limits.check_compact_threshold", return_value=(True, "70 min")), \
             patch("session_limits._write_breadcrumb_handoff"):
            new_state, msg = apply_session_limits(state)
            assert "HANDOFF.md updated" in msg
            assert new_state.warned is True

    def test_compact_only_fires_once(self, tmp_cwd, state):
        state.warned = True
        with patch("session_limits.check_thresholds", return_value=(False, "")), \
             patch("session_limits.check_compact_threshold", return_value=(True, "70 min")):
            _, msg = apply_session_limits(state)
            assert msg == ""

    def test_warning_returns_message(self, tmp_cwd, state):
        with patch("session_limits.check_thresholds", return_value=(False, "")), \
             patch("session_limits.check_compact_threshold", return_value=(False, "")), \
             patch("session_limits.should_warn", return_value=True):
            new_state, msg = apply_session_limits(state)
            assert "WARNING" in msg
            assert new_state.warned is True

    def test_no_limits_hit_returns_empty(self, tmp_cwd, state):
        with patch("session_limits.check_thresholds", return_value=(False, "")), \
             patch("session_limits.check_compact_threshold", return_value=(False, "")), \
             patch("session_limits.should_warn", return_value=False):
            _, msg = apply_session_limits(state)
            assert msg == ""
