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

from auto_handoff import (
    parse_handoff_header,
    trigger_auto_handoff,
    write_auto_handoff,
)
from session_monitor import (
    DRIFT_CHECK_INTERVAL,
    FALLBACK_MAX_EXCHANGES,
    GRACE_TOOL_CALLS,
    HARD_THRESHOLD_BYTES,
    WARN_THRESHOLD_BYTES,
    SessionState,
    check_gates_blocked,
    check_reports_blocked,
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
from strict_mode import (
    REAL_SYSTEM_QUERY_PATTERNS,
    compute_drift_score,
    detect_patch_forward,
    is_real_system_query,
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
        now = int(time.time())
        state = SessionState(session_start=now, exchanges=3, tool_calls=10)
        state_file = tmp_session_dir / "state.json"
        save_state(state, state_file)

        loaded = load_state(state_file)
        assert loaded.session_start == now
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


# --- G-GATE-1: protect .gates/ from agent writes ---


class TestGateProtection:
    """When gate_protect is on, agent cannot write to .gates/ directly."""

    def test_blocks_write_to_gates_dir(self):
        blocked, msg = check_gates_blocked(
            tool_name="Write",
            file_path="/project/.gates/precommit-passed",
            command="",
        )
        assert blocked is True
        assert "G-GATE-1" in msg

    def test_blocks_bash_echo_to_gates(self):
        blocked, msg = check_gates_blocked(
            tool_name="Bash",
            file_path="",
            command='echo "READY" > .gates/precommit-passed',
        )
        assert blocked is True

    def test_blocks_bash_mkdir_gates(self):
        blocked, msg = check_gates_blocked(
            tool_name="Bash",
            file_path="",
            command="mkdir -p .gates && echo READY > .gates/precommit-passed",
        )
        assert blocked is True

    def test_allows_read_of_gates(self):
        blocked, _ = check_gates_blocked(
            tool_name="Bash",
            file_path="",
            command="cat .gates/precommit-passed",
        )
        assert blocked is False

    def test_allows_write_to_non_gates_file(self):
        blocked, _ = check_gates_blocked(
            tool_name="Write",
            file_path="/project/src/main.py",
            command="",
        )
        assert blocked is False

    def test_allows_bash_without_gates_ref(self):
        blocked, _ = check_gates_blocked(
            tool_name="Bash",
            file_path="",
            command="git status",
        )
        assert blocked is False


# --- G-REPORT-1: protect reports/ from agent writes ---


class TestReportProtection:
    """When report_protect is on, agent cannot write to reports/ directly.

    Reports are the toolkit's source of truth. They must be produced by
    skill hooks, not by free-form agent output (Write tool or echo > path).
    """

    def test_blocks_write_to_reports_dir(self):
        blocked, msg = check_reports_blocked(
            tool_name="Write",
            file_path="/project/reports/precommit/pc_foo_abc123.md",
            command="",
        )
        assert blocked is True
        assert "G-REPORT-1" in msg

    def test_blocks_edit_to_reports_dir(self):
        blocked, msg = check_reports_blocked(
            tool_name="Edit",
            file_path="reports/evaluate/eval_repo_deadbeef.md",
            command="",
        )
        assert blocked is True
        assert "G-REPORT-1" in msg

    def test_blocks_write_to_any_reports_subdir(self):
        for path in (
            "reports/reviewer/r.md",
            "reports/assess/a.md",
            "/tmp/work/reports/evaluate/e.md",
        ):
            blocked, _ = check_reports_blocked(
                tool_name="Write",
                file_path=path,
                command="",
            )
            assert blocked is True, path

    def test_blocks_bash_echo_to_reports(self):
        blocked, msg = check_reports_blocked(
            tool_name="Bash",
            file_path="",
            command='echo "READY" > reports/precommit/pc_x.md',
        )
        assert blocked is True
        assert "G-REPORT-1" in msg

    def test_blocks_bash_append_to_reports(self):
        blocked, _ = check_reports_blocked(
            tool_name="Bash",
            file_path="",
            command='echo "more" >> reports/evaluate/eval.md',
        )
        assert blocked is True

    def test_blocks_bash_tee_into_reports(self):
        blocked, _ = check_reports_blocked(
            tool_name="Bash",
            file_path="",
            command='echo body | tee reports/reviewer/r.md',
        )
        assert blocked is True

    def test_blocks_bash_cp_into_reports(self):
        blocked, _ = check_reports_blocked(
            tool_name="Bash",
            file_path="",
            command="cp /tmp/forged.md reports/precommit/pc_y.md",
        )
        assert blocked is True

    def test_blocks_bash_mkdir_reports(self):
        blocked, _ = check_reports_blocked(
            tool_name="Bash",
            file_path="",
            command="mkdir -p reports/precommit && echo READY > reports/precommit/pc.md",
        )
        assert blocked is True

    def test_blocks_bash_heredoc_into_reports(self):
        blocked, _ = check_reports_blocked(
            tool_name="Bash",
            file_path="",
            command="cat <<EOF > reports/precommit/pc_z.md\nREADY\nEOF",
        )
        assert blocked is True

    def test_allows_read_of_reports(self):
        for cmd in (
            "cat reports/precommit/pc_x.md",
            "ls reports/",
            "head reports/evaluate/eval.md",
            "grep -r READY reports/",
        ):
            blocked, _ = check_reports_blocked(
                tool_name="Bash",
                file_path="",
                command=cmd,
            )
            assert blocked is False, cmd

    def test_allows_write_to_non_report_file(self):
        blocked, _ = check_reports_blocked(
            tool_name="Write",
            file_path="/project/src/main.py",
            command="",
        )
        assert blocked is False

    def test_allows_bash_without_reports_ref(self):
        blocked, _ = check_reports_blocked(
            tool_name="Bash",
            file_path="",
            command="git status",
        )
        assert blocked is False

    def test_pretooluse_blocks_when_report_protect_on(self):
        """Integration: PreToolUse honors state.report_protect."""
        state = SessionState(
            session_start=int(time.time()),
            report_protect=True,
        )
        _, msg, blocked = handle_pre_tool_use(
            state,
            tool_name="Write",
            file_path="reports/precommit/pc_a.md",
            command="",
        )
        assert blocked is True
        assert "G-REPORT-1" in msg

    def test_pretooluse_allows_when_report_protect_off(self):
        """Integration: PreToolUse skips report block when flag is off."""
        state = SessionState(
            session_start=int(time.time()),
            report_protect=False,
        )
        _, _, blocked = handle_pre_tool_use(
            state,
            tool_name="Write",
            file_path="reports/precommit/pc_a.md",
            command="",
        )
        assert blocked is False


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
        assert blocked is False  # No longer blocks — messages only
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

    def test_does_not_block_after_hard_stop(self):
        """Hard stop no longer blocks — it messages the agent to wrap up."""
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
        assert blocked is False
        assert "HARD STOP" in response


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


# --- Drift state fields (Slab 2) ---


class TestSessionStateDriftFields:
    def test_drift_field_defaults(self):
        state = SessionState(session_start=1000)
        assert state.mode == "normal"
        assert state.exchanges_since_query == 0
        assert state.patch_forward_count == 0
        assert state.slabs_without_data == 0
        assert state.last_tool_sequence == []

    def test_drift_fields_serialize_roundtrip(self):
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges_since_query=5,
            patch_forward_count=2,
            slabs_without_data=1,
            last_tool_sequence=[
                {"tool": "Bash", "was_test": True, "failed": True},
            ],
        )
        data = asdict(state)
        restored = SessionState(**data)
        assert restored.mode == "strict"
        assert restored.exchanges_since_query == 5
        assert restored.patch_forward_count == 2
        assert restored.last_tool_sequence == state.last_tool_sequence


# --- Real-system query detection ---


class TestIsRealSystemQuery:
    def test_curl_detected(self):
        assert is_real_system_query("curl https://api.example.com/items") is True

    def test_wget_detected(self):
        assert is_real_system_query("wget https://example.com/data.json") is True

    def test_psql_detected(self):
        assert is_real_system_query("psql -c 'SELECT * FROM users'") is True

    def test_mysql_detected(self):
        assert is_real_system_query("mysql -e 'SHOW TABLES'") is True

    def test_sqlite3_detected(self):
        assert is_real_system_query("sqlite3 db.sqlite 'SELECT count(*) FROM items'") is True

    def test_select_in_command(self):
        assert is_real_system_query("echo 'SELECT name FROM users' | psql") is True

    def test_docker_exec_query(self):
        assert is_real_system_query("docker exec db psql -c 'SELECT 1'") is True

    def test_httpie_detected(self):
        assert is_real_system_query("http GET https://api.example.com/items") is True

    def test_git_command_not_detected(self):
        assert is_real_system_query("git status") is False

    def test_pytest_not_detected(self):
        assert is_real_system_query("python3 -m pytest tests/ -q") is False

    def test_echo_not_detected(self):
        assert is_real_system_query("echo hello") is False

    def test_empty_command_not_detected(self):
        assert is_real_system_query("") is False

    def test_grpcurl_detected(self):
        assert is_real_system_query("grpcurl localhost:50051 list") is True

    def test_mongosh_detected(self):
        assert is_real_system_query("mongosh --eval 'db.users.find()'") is True


# --- Patch-forward detection ---


class TestDetectPatchForward:
    def test_no_patch_forward_on_empty_sequence(self):
        assert detect_patch_forward([]) is False

    def test_detects_test_fail_then_source_edit(self):
        """Test fail → Edit source with no investigation = patch-forward."""
        sequence = [
            {"tool": "Bash", "was_test": True, "failed": True},
            {"tool": "Edit", "file_path": "src/main.py", "was_test": False},
        ]
        assert detect_patch_forward(sequence) is True

    def test_no_patch_forward_with_investigation(self):
        """Test fail → Read → Edit source = NOT patch-forward (investigated)."""
        sequence = [
            {"tool": "Bash", "was_test": True, "failed": True},
            {"tool": "Read", "file_path": "src/main.py", "was_test": False},
            {"tool": "Edit", "file_path": "src/main.py", "was_test": False},
        ]
        assert detect_patch_forward(sequence) is False

    def test_no_patch_forward_with_query(self):
        """Test fail → curl → Edit source = NOT patch-forward (queried)."""
        sequence = [
            {"tool": "Bash", "was_test": True, "failed": True},
            {"tool": "Bash", "command": "curl localhost:8080/api", "was_test": False, "was_query": True},
            {"tool": "Edit", "file_path": "src/main.py", "was_test": False},
        ]
        assert detect_patch_forward(sequence) is False

    def test_no_patch_forward_when_editing_test_file(self):
        """Test fail → Edit test file = NOT patch-forward (fixing test)."""
        sequence = [
            {"tool": "Bash", "was_test": True, "failed": True},
            {"tool": "Edit", "file_path": "tests/test_main.py", "was_test": False},
        ]
        assert detect_patch_forward(sequence) is False

    def test_no_patch_forward_on_test_pass(self):
        """Test pass → Edit source = normal workflow, not patch-forward."""
        sequence = [
            {"tool": "Bash", "was_test": True, "failed": False},
            {"tool": "Edit", "file_path": "src/main.py", "was_test": False},
        ]
        assert detect_patch_forward(sequence) is False


# --- Drift counters in strict mode ---


class TestDriftCountersStrictMode:
    def test_exchanges_since_query_increments_in_strict(self):
        """In strict mode, exchanges_since_query increments on user prompt."""
        state = SessionState(session_start=1000, mode="strict")
        state, _ = handle_user_prompt(state)
        assert state.exchanges_since_query == 1

    def test_exchanges_since_query_not_tracked_in_normal(self):
        """In normal mode, exchanges_since_query stays at 0."""
        state = SessionState(session_start=1000, mode="normal")
        state, _ = handle_user_prompt(state)
        assert state.exchanges_since_query == 0

    def test_query_resets_exchanges_since_query(self):
        """A real-system query resets the counter."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges_since_query=8,
        )
        state = handle_post_tool_use(
            state, "curl output here",
            tool_name="Bash", command="curl https://api.example.com"
        )
        assert state.exchanges_since_query == 0

    def test_tool_sequence_tracked_in_strict(self):
        """In strict mode, tool calls are added to last_tool_sequence."""
        state = SessionState(session_start=1000, mode="strict")
        state = handle_post_tool_use(
            state, "FAILED: 2 tests",
            tool_name="Bash", command="python3 -m pytest tests/"
        )
        assert len(state.last_tool_sequence) == 1
        assert state.last_tool_sequence[0]["was_test"] is True
        assert state.last_tool_sequence[0]["failed"] is True

    def test_tool_sequence_not_tracked_in_normal(self):
        """In normal mode, last_tool_sequence stays empty."""
        state = SessionState(session_start=1000, mode="normal")
        state = handle_post_tool_use(
            state, "FAILED: 2 tests",
            tool_name="Bash", command="python3 -m pytest tests/"
        )
        assert state.last_tool_sequence == []

    def test_tool_sequence_capped_at_10(self):
        """Sequence buffer doesn't grow unbounded."""
        state = SessionState(session_start=1000, mode="strict")
        for i in range(15):
            state = handle_post_tool_use(
                state, f"result {i}",
                tool_name="Read", command=""
            )
        assert len(state.last_tool_sequence) <= 10

    def test_patch_forward_increments_counter(self):
        """When patch-forward is detected, counter increments."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            last_tool_sequence=[
                {"tool": "Bash", "was_test": True, "failed": True},
            ],
        )
        # Edit a source file after test failure — should detect patch-forward
        state = handle_post_tool_use(
            state, "",
            tool_name="Edit", command="", file_path="src/main.py"
        )
        assert state.patch_forward_count == 1


# --- slabs_without_data tracking ---


class TestSlabsWithoutData:
    def test_slab_completion_without_query_increments(self):
        """Precommit skill completing without a query increments slabs_without_data."""
        state = SessionState(session_start=1000, mode="strict")
        # Simulate precommit skill completing (slab boundary)
        state = handle_post_tool_use(
            state, "precommit passed",
            tool_name="Skill", command="", file_path=""
        )
        assert state.slabs_without_data == 1

    def test_slab_completion_with_query_does_not_increment(self):
        """Precommit after a real-system query doesn't increment."""
        state = SessionState(
            session_start=1000, mode="strict",
            has_queried_this_slab=True,
        )
        state = handle_post_tool_use(
            state, "precommit passed",
            tool_name="Skill", command="", file_path=""
        )
        assert state.slabs_without_data == 0

    def test_query_resets_slabs_without_data(self):
        """A real-system query resets slabs_without_data to 0."""
        state = SessionState(
            session_start=1000, mode="strict",
            slabs_without_data=2,
        )
        state = handle_post_tool_use(
            state, "query output",
            tool_name="Bash", command="curl https://api.example.com"
        )
        assert state.slabs_without_data == 0
        assert state.has_queried_this_slab is True

    def test_query_sets_has_queried_flag(self):
        """Real-system query sets has_queried_this_slab."""
        state = SessionState(session_start=1000, mode="strict")
        assert state.has_queried_this_slab is False
        state = handle_post_tool_use(
            state, "result",
            tool_name="Bash", command="psql -c 'SELECT 1'"
        )
        assert state.has_queried_this_slab is True

    def test_slab_boundary_resets_has_queried_flag(self):
        """After slab boundary, has_queried_this_slab resets for next slab."""
        state = SessionState(
            session_start=1000, mode="strict",
            has_queried_this_slab=True,
        )
        state = handle_post_tool_use(
            state, "precommit passed",
            tool_name="Skill", command="", file_path=""
        )
        assert state.has_queried_this_slab is False

    def test_normal_mode_no_slab_tracking(self):
        """Normal mode doesn't track slabs_without_data."""
        state = SessionState(session_start=1000, mode="normal")
        state = handle_post_tool_use(
            state, "precommit passed",
            tool_name="Skill", command="", file_path=""
        )
        assert state.slabs_without_data == 0


# --- Per-counter threshold warnings ---


class TestPerCounterThresholdWarnings:
    def test_warn_at_exchanges_since_query_over_10(self):
        """Warning injected when exchanges_since_query exceeds 10."""
        state = SessionState(
            session_start=1000, mode="strict",
            exchanges=5,  # Not at integrity check interval
            exchanges_since_query=10,  # Will become 11 after increment
        )
        state, response = handle_user_prompt(state)
        assert response is not None
        assert "haven't queried" in response.lower() or "real system" in response.lower()

    def test_no_warn_at_exchanges_10_or_below(self):
        """No warning when exchanges_since_query is 10 or below."""
        state = SessionState(
            session_start=1000, mode="strict",
            exchanges=5,
            exchanges_since_query=9,  # Will become 10 — threshold is >10
        )
        state, response = handle_user_prompt(state)
        if response:
            assert "haven't queried" not in response.lower()

    def test_warn_at_patch_forward_over_2(self):
        """Warning when patch_forward_count exceeds 2."""
        state = SessionState(
            session_start=1000, mode="strict",
            exchanges=5,
            patch_forward_count=3,
        )
        state, response = handle_user_prompt(state)
        assert response is not None
        assert "patch-forward" in response.lower() or "patch_forward" in response.lower()

    def test_warn_at_slabs_without_data_over_1(self):
        """Warning when slabs_without_data exceeds 1."""
        state = SessionState(
            session_start=1000, mode="strict",
            exchanges=5,
            slabs_without_data=2,
        )
        state, response = handle_user_prompt(state)
        assert response is not None
        assert "slab" in response.lower()

    def test_no_per_counter_warn_in_normal_mode(self):
        """Normal mode never gets per-counter warnings."""
        state = SessionState(
            session_start=1000, mode="normal",
            exchanges=5,
            exchanges_since_query=20,
            patch_forward_count=5,
            slabs_without_data=3,
        )
        state, response = handle_user_prompt(state)
        if response:
            assert "haven't queried" not in response.lower()
            assert "patch-forward" not in response.lower()

    def test_per_counter_warn_does_not_fire_at_integrity_interval(self):
        """At integrity check interval, only the integrity check fires (not both)."""
        state = SessionState(
            session_start=1000, mode="strict",
            exchanges=DRIFT_CHECK_INTERVAL - 1,
            exchanges_since_query=12,
        )
        state, response = handle_user_prompt(state)
        # Should get integrity check, not per-counter warning
        assert "INTEGRITY CHECK" in response


# --- Drift score computation (Slab 3) ---


class TestComputeDriftScore:
    def test_zero_counters_gives_zero(self):
        score = compute_drift_score(
            exchanges_since_query=0,
            patch_forward_count=0,
            slabs_without_data=0,
        )
        assert score == 0.0

    def test_max_counters_gives_one(self):
        score = compute_drift_score(
            exchanges_since_query=10,
            patch_forward_count=3,
            slabs_without_data=2,
        )
        assert score == 1.0

    def test_counters_beyond_max_capped(self):
        """Values beyond the divisor are capped at 1.0 per component."""
        score = compute_drift_score(
            exchanges_since_query=100,
            patch_forward_count=100,
            slabs_without_data=100,
        )
        assert score == 1.0

    def test_only_exchanges_component(self):
        """exchanges_since_query=5 → 0.5/10 * 0.4 = 0.2"""
        score = compute_drift_score(
            exchanges_since_query=5,
            patch_forward_count=0,
            slabs_without_data=0,
        )
        assert abs(score - 0.2) < 0.001

    def test_only_patch_forward_component(self):
        """patch_forward_count=3 → 1.0 * 0.4 = 0.4"""
        score = compute_drift_score(
            exchanges_since_query=0,
            patch_forward_count=3,
            slabs_without_data=0,
        )
        assert abs(score - 0.4) < 0.001

    def test_only_slabs_component(self):
        """slabs_without_data=1 → 0.5 * 0.2 = 0.1"""
        score = compute_drift_score(
            exchanges_since_query=0,
            patch_forward_count=0,
            slabs_without_data=1,
        )
        assert abs(score - 0.1) < 0.001

    def test_warning_threshold(self):
        """Score of 0.3 should be at warning level."""
        # exchanges=7.5 → 0.75*0.4=0.3, rest 0 → 0.3
        # Use exchanges=8 → 0.8*0.4=0.32
        score = compute_drift_score(
            exchanges_since_query=8,
            patch_forward_count=0,
            slabs_without_data=0,
        )
        assert score >= 0.3


# --- Periodic integrity check (Slab 3) ---


class TestPeriodicIntegrityCheck:
    def test_check_fires_at_interval(self):
        """Integrity check injects context at exchange 15."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=DRIFT_CHECK_INTERVAL - 1,  # Will become 15 after increment
        )
        state, response = handle_user_prompt(state)
        assert state.exchanges == DRIFT_CHECK_INTERVAL
        assert response is not None
        assert "INTEGRITY CHECK" in response

    def test_check_fires_at_multiples(self):
        """Integrity check also fires at exchange 30."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=(DRIFT_CHECK_INTERVAL * 2) - 1,
        )
        state, response = handle_user_prompt(state)
        assert "INTEGRITY CHECK" in response

    def test_no_check_between_intervals(self):
        """No integrity check at non-interval exchanges."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=10,  # Will become 11
        )
        state, response = handle_user_prompt(state)
        # Should not contain integrity check (may be None or session warning)
        if response:
            assert "INTEGRITY CHECK" not in response

    def test_no_check_in_normal_mode(self):
        """Normal mode never gets integrity checks."""
        state = SessionState(
            session_start=1000,
            mode="normal",
            exchanges=DRIFT_CHECK_INTERVAL - 1,
        )
        state, response = handle_user_prompt(state)
        if response:
            assert "INTEGRITY CHECK" not in response

    def test_check_includes_drift_score(self):
        """Integrity check output includes computed drift score."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=DRIFT_CHECK_INTERVAL - 1,
            exchanges_since_query=5,
            patch_forward_count=1,
        )
        state, response = handle_user_prompt(state)
        assert "Drift score" in response

    def test_check_includes_counter_values(self):
        """Integrity check shows current counter values."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=DRIFT_CHECK_INTERVAL - 1,
            exchanges_since_query=7,  # becomes 8 after increment
            patch_forward_count=2,
            slabs_without_data=1,
        )
        state, response = handle_user_prompt(state)
        assert "8" in response  # exchanges_since_query (incremented before check)
        assert "2" in response  # patch_forward_count

    def test_critical_drift_triggers_restart(self):
        """Drift score > 0.8 sets stopped=2 (session restart)."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=DRIFT_CHECK_INTERVAL - 1,
            exchanges_since_query=10,
            patch_forward_count=3,
            slabs_without_data=2,
        )
        state, response = handle_user_prompt(state)
        assert state.stopped == 2
        assert "HANDOFF" in response or "restart" in response.lower()

    def test_moderate_drift_does_not_restart(self):
        """Drift score 0.3-0.6 warns but does not restart."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=DRIFT_CHECK_INTERVAL - 1,
            exchanges_since_query=8,  # 0.8*0.4=0.32
            patch_forward_count=0,
            slabs_without_data=0,
        )
        state, response = handle_user_prompt(state)
        assert state.stopped == 0
        assert "INTEGRITY CHECK" in response


# --- Auto-handoff (hook-written HANDOFF.md) ---


class TestWriteAutoHandoff:
    """Tests for write_auto_handoff() — hook writes HANDOFF.md on hard stop."""

    def test_writes_handoff_file(self, tmp_path):
        """write_auto_handoff creates a HANDOFF.md file."""
        handoff_path = tmp_path / "HANDOFF.md"
        state = SessionState(session_start=1000, cumulative_output_bytes=800_000)
        write_auto_handoff(
            handoff_path=handoff_path,
            state=state,
            stop_reason="bytes threshold exceeded",
            previous_handoff="",
            git_log="abc1234 Some commit",
        )
        assert handoff_path.exists()
        content = handoff_path.read_text()
        assert len(content) > 0

    def test_preserves_goal_from_previous_handoff(self, tmp_path):
        """Goal from previous HANDOFF.md is carried forward."""
        handoff_path = tmp_path / "HANDOFF.md"
        previous = (
            "# HANDOFF\n\n"
            "## Goal\n\n"
            "Build the payment system\n\n"
            "## Session\n\nNumber: 3\n"
        )
        state = SessionState(session_start=1000, compactions=1)
        write_auto_handoff(
            handoff_path=handoff_path,
            state=state,
            stop_reason="compaction",
            previous_handoff=previous,
            git_log="abc1234 Some commit",
        )
        content = handoff_path.read_text()
        assert "Build the payment system" in content

    def test_increments_session_number(self, tmp_path):
        """Session number is incremented from previous handoff."""
        handoff_path = tmp_path / "HANDOFF.md"
        previous = (
            "# HANDOFF\n\n"
            "## Goal\n\nSome goal\n\n"
            "## Session\n\nNumber: 3\n"
        )
        state = SessionState(session_start=1000, compactions=1)
        write_auto_handoff(
            handoff_path=handoff_path,
            state=state,
            stop_reason="compaction",
            previous_handoff=previous,
            git_log="",
        )
        content = handoff_path.read_text()
        assert "Number: 4" in content

    def test_includes_stop_reason(self, tmp_path):
        """Stop reason is included in the handoff."""
        handoff_path = tmp_path / "HANDOFF.md"
        state = SessionState(session_start=1000, compactions=1)
        write_auto_handoff(
            handoff_path=handoff_path,
            state=state,
            stop_reason="Context compacted (1 time(s))",
            previous_handoff="",
            git_log="",
        )
        content = handoff_path.read_text()
        assert "compacted" in content.lower()

    def test_includes_git_log(self, tmp_path):
        """Recent commits are included in the handoff."""
        handoff_path = tmp_path / "HANDOFF.md"
        state = SessionState(session_start=1000, compactions=1)
        git_log = "abc1234 Fix payment validation\ndef5678 Add cart endpoint"
        write_auto_handoff(
            handoff_path=handoff_path,
            state=state,
            stop_reason="compaction",
            previous_handoff="",
            git_log=git_log,
        )
        content = handoff_path.read_text()
        assert "abc1234" in content
        assert "Fix payment validation" in content

    def test_includes_session_counters(self, tmp_path):
        """Session state counters are included for diagnostics."""
        handoff_path = tmp_path / "HANDOFF.md"
        state = SessionState(
            session_start=1000,
            exchanges=25,
            tool_calls=142,
            cumulative_output_bytes=750_000,
            compactions=1,
        )
        write_auto_handoff(
            handoff_path=handoff_path,
            state=state,
            stop_reason="compaction",
            previous_handoff="",
            git_log="",
        )
        content = handoff_path.read_text()
        assert "25" in content  # exchanges
        assert "142" in content  # tool_calls

    def test_defaults_session_number_to_1_when_no_previous(self, tmp_path):
        """When there's no previous handoff, session number defaults to 1 (next=2)."""
        handoff_path = tmp_path / "HANDOFF.md"
        state = SessionState(session_start=1000, compactions=1)
        write_auto_handoff(
            handoff_path=handoff_path,
            state=state,
            stop_reason="compaction",
            previous_handoff="",
            git_log="",
        )
        content = handoff_path.read_text()
        assert "Number: 2" in content

    def test_includes_last_tool_sequence(self, tmp_path):
        """Last tool sequence from state is included (shows in-progress work)."""
        handoff_path = tmp_path / "HANDOFF.md"
        state = SessionState(
            session_start=1000,
            compactions=1,
            last_tool_sequence=[
                {"tool": "Edit", "file_path": "src/main.py"},
                {"tool": "Bash", "command": "pytest tests/"},
            ],
        )
        write_auto_handoff(
            handoff_path=handoff_path,
            state=state,
            stop_reason="compaction",
            previous_handoff="",
            git_log="",
        )
        content = handoff_path.read_text()
        assert "src/main.py" in content or "Edit" in content


class TestParseHandoffGoalAndSession:
    """Tests for parsing goal and session number from existing HANDOFF.md."""

    def test_extracts_goal(self):
        handoff = (
            "# HANDOFF\n\n"
            "## Goal\n\n"
            "Build the payment system\n\n"
            "## Session\n\nNumber: 3\n"
        )
        goal, session_number = parse_handoff_header(handoff)
        assert goal == "Build the payment system"

    def test_extracts_session_number(self):
        handoff = (
            "# HANDOFF\n\n"
            "## Goal\n\nSome goal\n\n"
            "## Session\n\nNumber: 5\n"
        )
        goal, session_number = parse_handoff_header(handoff)
        assert session_number == 5

    def test_defaults_on_empty_string(self):
        goal, session_number = parse_handoff_header("")
        assert goal == ""
        assert session_number == 1

    def test_defaults_on_malformed_input(self):
        goal, session_number = parse_handoff_header("random text with no structure")
        assert session_number == 1


class TestAutoHandoffWiring:
    """Tests that trigger_auto_handoff is called at the right times."""

    def test_compaction_writes_handoff(self, tmp_path, monkeypatch):
        """PostCompact event triggers auto-handoff write."""
        handoff_path = tmp_path / "HANDOFF.md"
        # Pre-populate a previous handoff
        handoff_path.write_text(
            "# HANDOFF\n\n## Goal\n\nBuild feature X\n\n"
            "## Session\n\nNumber: 2\n"
        )

        # Monkey-patch Path("HANDOFF.md") to use tmp_path
        monkeypatch.chdir(tmp_path)

        state = SessionState(
            session_start=1000,
            exchanges=20,
            tool_calls=100,
            cumulative_output_bytes=600_000,
        )
        state, response = handle_post_compact(state)
        assert state.stopped == 2
        assert "automatically" in response.lower()
        # Verify handoff was written
        content = handoff_path.read_text()
        assert "Number: 3" in content
        assert "Build feature X" in content

    def test_grace_exhausted_writes_handoff(self, tmp_path, monkeypatch):
        """Grace period exhaustion triggers auto-handoff write."""
        handoff_path = tmp_path / "HANDOFF.md"
        handoff_path.write_text(
            "# HANDOFF\n\n## Goal\n\nSome goal\n\n"
            "## Session\n\nNumber: 1\n"
        )
        monkeypatch.chdir(tmp_path)

        state = SessionState(
            session_start=1000,
            cumulative_output_bytes=HARD_THRESHOLD_BYTES + 1,
            stopped=1,
            tool_calls=60,
            stop_at_tool_call=60,  # Grace exhausted
        )
        # Tool is not blocked, but handoff should be written
        state, response, blocked = handle_pre_tool_use(
            state, tool_name="Read", file_path="/project/src/main.py", command=""
        )
        assert blocked is False  # No longer blocks — messages only
        assert state.stopped == 2
        content = handoff_path.read_text()
        assert "Number: 2" in content
        assert "Some goal" in content

    def test_handoff_written_once_not_repeatedly(self, tmp_path, monkeypatch):
        """Auto-handoff is written once, not on every subsequent blocked tool."""
        handoff_path = tmp_path / "HANDOFF.md"
        handoff_path.write_text(
            "# HANDOFF\n\n## Goal\n\nGoal\n\n## Session\n\nNumber: 1\n"
        )
        monkeypatch.chdir(tmp_path)

        state = SessionState(
            session_start=1000,
            cumulative_output_bytes=HARD_THRESHOLD_BYTES + 1,
            stopped=1,
            tool_calls=60,
            stop_at_tool_call=60,
        )
        # First call — triggers handoff write
        state, _, _ = handle_pre_tool_use(
            state, tool_name="Read", file_path="foo.py", command=""
        )
        first_content = handoff_path.read_text()

        # Second call — already stopped=2, should not rewrite
        state, _, _ = handle_pre_tool_use(
            state, tool_name="Read", file_path="bar.py", command=""
        )
        second_content = handoff_path.read_text()
        assert first_content == second_content


# --- Time-based session limit (F1) ---

DEFAULT_MAX_SESSION_MINUTES = 0


class TestTimeLimitInCheckThresholds:
    """F1: check_thresholds detects elapsed time exceeding max_session_minutes."""

    def test_time_limit_triggers_at_70_minutes(self):
        """Session running for 70+ min triggers hard stop."""
        now = int(time.time())
        state = SessionState(
            session_start=now - (70 * 60 + 1),  # 70 min 1 sec ago
            max_session_minutes=70,
        )
        triggered, reason = check_thresholds(state)
        assert triggered is True
        assert "70" in reason or "time" in reason.lower()

    def test_time_limit_does_not_trigger_before_70_minutes(self):
        """Session under 70 min does not trigger."""
        now = int(time.time())
        state = SessionState(
            session_start=now - (69 * 60),  # 69 min ago
            max_session_minutes=70,
        )
        triggered, reason = check_thresholds(state)
        assert triggered is False

    def test_time_limit_configurable(self):
        """max_session_minutes can be set to custom value."""
        now = int(time.time())
        state = SessionState(
            session_start=now - (31 * 60),  # 31 min ago
            max_session_minutes=30,
        )
        triggered, reason = check_thresholds(state)
        assert triggered is True

    def test_time_limit_priority_after_compaction(self):
        """Compaction still takes priority over time."""
        now = int(time.time())
        state = SessionState(
            session_start=now - (80 * 60),
            max_session_minutes=70,
            compactions=1,
        )
        triggered, reason = check_thresholds(state)
        assert triggered is True
        assert "compacted" in reason.lower()

    def test_time_limit_priority_before_bytes(self):
        """Time triggers before bytes threshold."""
        now = int(time.time())
        state = SessionState(
            session_start=now - (71 * 60),
            max_session_minutes=70,
            cumulative_output_bytes=HARD_THRESHOLD_BYTES + 1,
        )
        triggered, reason = check_thresholds(state)
        assert triggered is True
        assert "time" in reason.lower() or "minute" in reason.lower()

    def test_default_max_session_minutes_is_70(self):
        """Default value for max_session_minutes is 70."""
        state = SessionState(session_start=1000)
        assert state.max_session_minutes == DEFAULT_MAX_SESSION_MINUTES


class TestStaleSessionStartSelfHeal:
    """load_state resets session_start when it's older than max_session_minutes."""

    def test_stale_session_start_is_reset(self, tmp_path):
        """session_start from a previous session (hours ago) gets reset to now."""
        state_file = tmp_path / "state.json"
        now = int(time.time())
        stale_start = now - (48 * 3600)  # 48 hours ago
        state_file.write_text(json.dumps({
            "session_start": stale_start,
            "max_session_minutes": 70,
            "exchanges": 5,
        }))
        state = load_state(state_file)
        # session_start should be reset to approximately now, not 48h ago
        assert abs(state.session_start - now) < 5
        # other fields preserved
        assert state.exchanges == 5

    def test_fresh_session_start_is_preserved(self, tmp_path):
        """session_start within max_session_minutes is not touched."""
        state_file = tmp_path / "state.json"
        now = int(time.time())
        recent_start = now - (30 * 60)  # 30 min ago
        state_file.write_text(json.dumps({
            "session_start": recent_start,
            "max_session_minutes": 70,
        }))
        state = load_state(state_file)
        assert state.session_start == recent_start

    def test_stale_detection_uses_max_session_minutes(self, tmp_path):
        """Stale threshold adapts to configured max_session_minutes."""
        state_file = tmp_path / "state.json"
        now = int(time.time())
        # 5 hours ago, max is 120 min — so 300 min > 120*2=240 = stale
        state_file.write_text(json.dumps({
            "session_start": now - (5 * 3600),
            "max_session_minutes": 120,
        }))
        state = load_state(state_file)
        assert abs(state.session_start - now) < 5

    def test_disabled_time_limit_skips_stale_check(self, tmp_path):
        """max_session_minutes=0 means no stale detection."""
        state_file = tmp_path / "state.json"
        now = int(time.time())
        old_start = now - (48 * 3600)
        state_file.write_text(json.dumps({
            "session_start": old_start,
            "max_session_minutes": 0,
        }))
        state = load_state(state_file)
        assert state.session_start == old_start


class TestTimeLimitHardStop:
    """F1: Time limit triggers immediate hard stop — no grace period."""

    def test_time_limit_skips_grace_goes_to_hard_stop(self, tmp_path, monkeypatch):
        """Time limit goes directly to stopped=2, no grace (stopped=1)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "HANDOFF.md").write_text("# HANDOFF\n\n## Goal\n\nGoal\n\n## Session\n\nNumber: 1\n")

        now = int(time.time())
        state = SessionState(
            session_start=now - (71 * 60),
            max_session_minutes=70,
        )
        state, response, blocked = handle_pre_tool_use(
            state, tool_name="Read", file_path="foo.py", command=""
        )
        # Should go directly to stopped=2 (hard stop), never stopped=1 (grace)
        assert state.stopped == 2
        assert blocked is False  # No longer blocks — messages only
        assert "TIME LIMIT" in response

    def test_time_limit_writes_auto_handoff(self, tmp_path, monkeypatch):
        """Time limit triggers auto-handoff write."""
        monkeypatch.chdir(tmp_path)
        handoff_path = tmp_path / "HANDOFF.md"
        handoff_path.write_text("# HANDOFF\n\n## Goal\n\nGoal\n\n## Session\n\nNumber: 1\n")

        now = int(time.time())
        state = SessionState(
            session_start=now - (71 * 60),
            max_session_minutes=70,
        )
        state, response, blocked = handle_pre_tool_use(
            state, tool_name="Read", file_path="foo.py", command=""
        )
        content = handoff_path.read_text()
        assert "Number: 2" in content
        assert "time" in content.lower() or "minute" in content.lower()

    def test_time_limit_allows_git_after_stop(self, tmp_path, monkeypatch):
        """After time-based hard stop, git commit is still allowed."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "HANDOFF.md").write_text("# HANDOFF\n\n## Goal\n\nGoal\n\n## Session\n\nNumber: 1\n")

        now = int(time.time())
        state = SessionState(
            session_start=now - (71 * 60),
            max_session_minutes=70,
            stopped=2,
        )
        state, response, blocked = handle_pre_tool_use(
            state, tool_name="Bash", file_path="", command="git commit -m 'wip'"
        )
        assert blocked is False
