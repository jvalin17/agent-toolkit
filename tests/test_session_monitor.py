"""Tests for hooks/session_monitor.py — context-based session monitoring."""

import json
import os
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest

# Add hooks/ to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from session_monitor import (
    FALLBACK_MAX_EXCHANGES,
    GRACE_TOOL_CALLS,
    HARD_THRESHOLD_BYTES,
    WARN_THRESHOLD_BYTES,
    SessionState,
    check_session_blocked,
    check_thresholds,
    handle_post_compact,
    handle_post_tool_use,
    handle_pre_tool_use,
    handle_user_prompt,
    load_state,
    make_hook_response,
    save_state,
)


@pytest.fixture
def tmp_session_dir(tmp_path):
    """Create a temporary .session directory."""
    session_dir = tmp_path / ".session"
    session_dir.mkdir()
    return session_dir


@pytest.fixture
def fresh_state():
    """Return a fresh SessionState with current timestamp."""
    return SessionState(session_start=int(time.time()))


# --- SessionState dataclass ---


class TestSessionState:
    def test_defaults(self):
        state = SessionState(session_start=1000)
        assert state.exchanges == 0
        assert state.tool_calls == 0
        assert state.cumulative_output_bytes == 0
        assert state.compactions == 0
        assert state.warned is False
        assert state.stopped == 0
        assert state.stop_at_tool_call == 0

    def test_serialization_roundtrip(self):
        state = SessionState(
            session_start=1000,
            exchanges=5,
            tool_calls=42,
            cumulative_output_bytes=350000,
            compactions=1,
            warned=True,
            stopped=1,
            stop_at_tool_call=52,
        )
        data = asdict(state)
        restored = SessionState(**data)
        assert restored == state


# --- State persistence ---


class TestStatePersistence:
    def test_save_and_load(self, tmp_session_dir):
        state = SessionState(session_start=1000, exchanges=3, tool_calls=10)
        state_file = tmp_session_dir / "state.json"
        save_state(state, state_file)

        loaded = load_state(state_file)
        assert loaded.session_start == 1000
        assert loaded.exchanges == 3
        assert loaded.tool_calls == 10

    def test_load_missing_file_returns_fresh(self, tmp_session_dir):
        state_file = tmp_session_dir / "state.json"
        loaded = load_state(state_file)
        assert loaded.exchanges == 0
        assert loaded.tool_calls == 0
        assert loaded.cumulative_output_bytes == 0

    def test_save_is_atomic(self, tmp_session_dir):
        """Save writes to temp file then renames — no partial writes."""
        state = SessionState(session_start=1000, exchanges=5)
        state_file = tmp_session_dir / "state.json"
        save_state(state, state_file)

        # File should be valid JSON
        data = json.loads(state_file.read_text())
        assert data["exchanges"] == 5

    def test_load_corrupted_file_returns_fresh(self, tmp_session_dir):
        state_file = tmp_session_dir / "state.json"
        state_file.write_text("not json {{{")
        loaded = load_state(state_file)
        assert loaded.exchanges == 0


# --- Threshold detection ---


class TestThresholds:
    def test_no_trigger_when_fresh(self, fresh_state):
        triggered, reason = check_thresholds(fresh_state)
        assert triggered is False
        assert reason == ""

    def test_compaction_triggers_immediately(self, fresh_state):
        fresh_state.compactions = 1
        triggered, reason = check_thresholds(fresh_state)
        assert triggered is True
        assert "compact" in reason.lower()

    def test_bytes_hard_threshold_triggers(self, fresh_state):
        fresh_state.cumulative_output_bytes = HARD_THRESHOLD_BYTES + 1
        triggered, reason = check_thresholds(fresh_state)
        assert triggered is True
        assert "byte" in reason.lower() or "output" in reason.lower()

    def test_bytes_warn_threshold_does_not_trigger(self, fresh_state):
        """Warn threshold is not a hard trigger — just advisory."""
        fresh_state.cumulative_output_bytes = WARN_THRESHOLD_BYTES + 1
        triggered, reason = check_thresholds(fresh_state)
        assert triggered is False

    def test_exchange_count_does_not_trigger(self, fresh_state):
        """Exchanges alone never trigger — only bytes and compaction matter."""
        fresh_state.exchanges = FALLBACK_MAX_EXCHANGES
        triggered, reason = check_thresholds(fresh_state)
        assert triggered is False

    def test_warn_check_at_70_percent(self, fresh_state):
        """Should warn when bytes exceed warn threshold."""
        fresh_state.cumulative_output_bytes = WARN_THRESHOLD_BYTES + 1
        # check_thresholds returns hard trigger only; warn is separate
        triggered, _ = check_thresholds(fresh_state)
        assert triggered is False  # Not a hard trigger

    def test_compaction_takes_priority_over_bytes(self, fresh_state):
        """If both compaction and bytes trigger, reason mentions compaction."""
        fresh_state.compactions = 1
        fresh_state.cumulative_output_bytes = HARD_THRESHOLD_BYTES + 1
        triggered, reason = check_thresholds(fresh_state)
        assert triggered is True
        assert "compact" in reason.lower()


# --- G-SESSION-1 enforcement ---


class TestSessionBlocking:
    def test_blocks_write_to_session_dir(self):
        blocked, msg = check_session_blocked(
            tool_name="Write",
            file_path="/project/.session/state.json",
            command="",
        )
        assert blocked is True
        assert "G-SESSION-1" in msg

    def test_blocks_edit_to_session_dir(self):
        blocked, msg = check_session_blocked(
            tool_name="Edit",
            file_path="/project/.session/state.json",
            command="",
        )
        assert blocked is True

    def test_blocks_bash_write_to_session(self):
        blocked, msg = check_session_blocked(
            tool_name="Bash",
            file_path="",
            command="echo 'test' > .session/state",
        )
        assert blocked is True

    def test_allows_bash_read_of_session(self):
        blocked, _ = check_session_blocked(
            tool_name="Bash",
            file_path="",
            command="cat .session/state",
        )
        assert blocked is False

    def test_allows_write_to_non_session_file(self):
        blocked, _ = check_session_blocked(
            tool_name="Write",
            file_path="/project/src/main.py",
            command="",
        )
        assert blocked is False

    def test_allows_bash_without_session_ref(self):
        blocked, _ = check_session_blocked(
            tool_name="Bash",
            file_path="",
            command="git status",
        )
        assert blocked is False

    def test_blocks_rm_session(self):
        blocked, _ = check_session_blocked(
            tool_name="Bash",
            file_path="",
            command="rm -rf .session/",
        )
        assert blocked is True

    def test_blocks_mkdir_session(self):
        blocked, _ = check_session_blocked(
            tool_name="Bash",
            file_path="",
            command="mkdir .session/foo",
        )
        assert blocked is True


# --- Event handlers ---


class TestHandleUserPrompt:
    def test_increments_exchange_count(self, fresh_state):
        result_state, response = handle_user_prompt(fresh_state)
        assert result_state.exchanges == 1

    def test_warns_on_bytes_threshold(self):
        """Warns when bytes exceed threshold, regardless of exchange count."""
        state = SessionState(
            session_start=int(time.time()),
            exchanges=5,
            cumulative_output_bytes=WARN_THRESHOLD_BYTES + 1,
        )
        result_state, response = handle_user_prompt(state)
        assert result_state.warned is True

    def test_no_warn_on_exchanges_alone(self):
        """High exchange count without high bytes should NOT warn."""
        state = SessionState(
            session_start=int(time.time()),
            exchanges=FALLBACK_MAX_EXCHANGES - 1,
            cumulative_output_bytes=0,
        )
        result_state, response = handle_user_prompt(state)
        assert result_state.warned is False


class TestHandlePostToolUse:
    def test_tracks_output_bytes(self, fresh_state):
        tool_result = "x" * 5000  # 5KB output
        result_state = handle_post_tool_use(fresh_state, tool_result)
        assert result_state.cumulative_output_bytes == 5000

    def test_accumulates_bytes(self, fresh_state):
        fresh_state.cumulative_output_bytes = 10000
        tool_result = "x" * 3000
        result_state = handle_post_tool_use(fresh_state, tool_result)
        assert result_state.cumulative_output_bytes == 13000

    def test_handles_empty_result(self, fresh_state):
        result_state = handle_post_tool_use(fresh_state, "")
        assert result_state.cumulative_output_bytes == 0


class TestHandlePostCompact:
    def test_increments_compaction_count(self, fresh_state):
        result_state, response = handle_post_compact(fresh_state)
        assert result_state.compactions == 1

    def test_triggers_handoff_on_first_compact(self, fresh_state):
        result_state, response = handle_post_compact(fresh_state)
        assert response is not None
        assert "context" in response.lower() or "handoff" in response.lower()


class TestHandlePreToolUse:
    def test_increments_tool_calls(self, fresh_state):
        result_state, response, blocked = handle_pre_tool_use(
            fresh_state, tool_name="Read", file_path="", command=""
        )
        assert result_state.tool_calls == 1
        assert blocked is False

    def test_blocks_session_write(self, fresh_state):
        result_state, response, blocked = handle_pre_tool_use(
            fresh_state,
            tool_name="Write",
            file_path="/project/.session/foo",
            command="",
        )
        assert blocked is True
        assert "G-SESSION-1" in response

    def test_grace_period_starts_on_threshold(self):
        state = SessionState(
            session_start=int(time.time()),
            cumulative_output_bytes=HARD_THRESHOLD_BYTES + 1,
            tool_calls=50,
        )
        result_state, response, blocked = handle_pre_tool_use(
            state, tool_name="Read", file_path="", command=""
        )
        assert result_state.stopped == 1
        assert result_state.stop_at_tool_call == 51 + GRACE_TOOL_CALLS
        assert blocked is False  # Grace period allows

    def test_hard_stop_after_grace_exhausted(self):
        state = SessionState(
            session_start=int(time.time()),
            cumulative_output_bytes=HARD_THRESHOLD_BYTES + 1,
            stopped=1,
            tool_calls=60,
            stop_at_tool_call=60,  # Grace exhausted
        )
        result_state, response, blocked = handle_pre_tool_use(
            state, tool_name="Read", file_path="/project/src/main.py", command=""
        )
        assert blocked is True
        assert "HARD STOP" in response

    def test_allows_handoff_write_after_hard_stop(self):
        state = SessionState(
            session_start=int(time.time()),
            cumulative_output_bytes=HARD_THRESHOLD_BYTES + 1,
            stopped=1,
            tool_calls=60,
            stop_at_tool_call=60,
        )
        result_state, response, blocked = handle_pre_tool_use(
            state,
            tool_name="Write",
            file_path="/project/HANDOFF.md",
            command="",
        )
        assert blocked is False

    def test_allows_git_commit_after_hard_stop(self):
        state = SessionState(
            session_start=int(time.time()),
            cumulative_output_bytes=HARD_THRESHOLD_BYTES + 1,
            stopped=1,
            tool_calls=60,
            stop_at_tool_call=60,
        )
        result_state, response, blocked = handle_pre_tool_use(
            state,
            tool_name="Bash",
            file_path="",
            command="git commit -m 'handoff'",
        )
        assert blocked is False

    def test_blocks_non_handoff_after_hard_stop(self):
        state = SessionState(
            session_start=int(time.time()),
            cumulative_output_bytes=HARD_THRESHOLD_BYTES + 1,
            stopped=1,
            tool_calls=60,
            stop_at_tool_call=60,
        )
        result_state, response, blocked = handle_pre_tool_use(
            state,
            tool_name="Bash",
            file_path="",
            command="npm run build",
        )
        assert blocked is True


# --- JSON output format ---


class TestHookResponse:
    def test_makes_valid_json(self):
        response = make_hook_response("PreToolUse", "test message")
        data = json.loads(response)
        assert data["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert data["hookSpecificOutput"]["additionalContext"] == "test message"

    def test_escapes_special_chars(self):
        response = make_hook_response("PreToolUse", 'message with "quotes" and\nnewlines')
        data = json.loads(response)
        assert '"quotes"' in data["hookSpecificOutput"]["additionalContext"]
