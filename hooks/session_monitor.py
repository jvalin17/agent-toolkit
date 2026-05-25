#!/usr/bin/env python3
"""Session monitor hook — context-based session limits.

Context-pressure detection:
- Cumulative tool output bytes (PostToolUse)
- Compaction events (PostCompact)
- Exchange count fallback (raised threshold)

Single script, multiple events. Reads hook_event_name from stdin JSON
and dispatches to the appropriate handler.

Fires on: PreToolUse, PostToolUse, UserPromptSubmit, PostCompact
State: .session/state.json
"""

import json
import sys
from pathlib import Path
from typing import Optional

from auto_handoff import trigger_auto_handoff
from path_protection import (
    check_gates_blocked,
    check_protected_paths,
    check_reports_blocked,
    check_session_blocked,
)
from session_limits import apply_session_limits
from session_state import (
    FALLBACK_MAX_EXCHANGES,
    GRACE_TOOL_CALLS,
    HARD_THRESHOLD_BYTES,
    SESSION_DIR,
    STATE_FILENAME,
    WARN_THRESHOLD_BYTES,
    SessionState,
    check_thresholds,
    load_state,
    make_hook_response,
    save_state,
    should_warn,
)
from strict_mode import (
    compute_drift_score,
    detect_patch_forward,
    is_real_system_query,
    is_test_command,
    is_test_failure,
    is_test_file,
)

MAX_TOOL_SEQUENCE_LENGTH = 10
DRIFT_CHECK_INTERVAL = 15  # Integrity check every N exchanges in strict mode

EXCHANGES_WARN_THRESHOLD = 10
PATCH_FORWARD_WARN_THRESHOLD = 2
SLABS_WITHOUT_DATA_WARN_THRESHOLD = 1
LAST_TEST_EDITS_MAX = 5


def _strict_integrity_response(state: SessionState) -> Optional[str]:
    """Periodic strict-mode integrity check (every DRIFT_CHECK_INTERVAL exchanges)."""
    drift = compute_drift_score(
        state.exchanges_since_query,
        state.patch_forward_count,
        state.slabs_without_data,
    )
    response = (
        f"STRICT MODE INTEGRITY CHECK (exchange {state.exchanges}):\n"
        f"- Exchanges since last real-system query: {state.exchanges_since_query}\n"
        f"- Patch-forward incidents this session: {state.patch_forward_count}\n"
        f"- Slabs without data queries: {state.slabs_without_data}\n"
        f"- Drift score: {drift:.2f}\n"
    )
    if drift > 0.8:
        response += (
            "\nCRITICAL DRIFT: Score exceeds 0.8. SESSION RESTART required.\n"
            "Write HANDOFF.md immediately and exit. "
            "The auto-continuation wrapper will relaunch a fresh session."
        )
        state.stopped = 2
    elif drift > 0.6:
        response += (
            "\nHIGH DRIFT: Score exceeds 0.6. "
            "Do NOT start new slabs. Query the real system before continuing."
        )
    elif drift > 0.3:
        response += (
            "\nMODERATE DRIFT: Score exceeds 0.3. "
            "Consider querying the real system to ground your work."
        )
    return response


def _strict_drift_warnings(state: SessionState) -> Optional[str]:
    warnings = []
    if state.exchanges_since_query > EXCHANGES_WARN_THRESHOLD:
        warnings.append(
            f"You haven't queried the real system in "
            f"{state.exchanges_since_query} exchanges. "
            f"Are you working from inference?"
        )
    if state.patch_forward_count > PATCH_FORWARD_WARN_THRESHOLD:
        warnings.append(
            f"Patch-forward pattern detected "
            f"{state.patch_forward_count} times. "
            f"Stop and investigate root causes."
        )
    if state.slabs_without_data > SLABS_WITHOUT_DATA_WARN_THRESHOLD:
        warnings.append(
            f"{state.slabs_without_data} slabs completed with no "
            f"real-system queries. This slab requires data evidence "
            f"before continuing."
        )
    if warnings:
        return "STRICT MODE WARNING:\n- " + "\n- ".join(warnings)
    return None


def handle_user_prompt(state: SessionState) -> tuple:
    """Handle UserPromptSubmit event. Increments exchanges, checks warn."""
    state.exchanges += 1

    if state.mode == "strict":
        state.exchanges_since_query += 1

    if state.mode == "strict" and state.exchanges % DRIFT_CHECK_INTERVAL == 0:
        return state, _strict_integrity_response(state)

    if state.mode == "strict":
        warning = _strict_drift_warnings(state)
        if warning:
            return state, warning

    if should_warn(state):
        state.warned = True
        return state, (
            f"SESSION WARNING: {state.exchanges}/{FALLBACK_MAX_EXCHANGES} exchanges, "
            f"{state.cumulative_output_bytes:,}/{HARD_THRESHOLD_BYTES:,} bytes. "
            f"Context pressure building. Finish the current safe stopping point "
            f"and prepare HANDOFF.md. Do not start new slabs or features."
        )

    return state, None


def handle_post_tool_use(
    state: SessionState,
    tool_result: str,
    tool_name: str = "",
    command: str = "",
    file_path: str = "",
) -> SessionState:
    """Handle PostToolUse event. Tracks cumulative output bytes and drift."""
    state.cumulative_output_bytes += len(tool_result)

    if tool_name in ("Edit", "Write") and is_test_file(file_path):
        state.last_test_edits.append(file_path)
        state.last_test_edits = state.last_test_edits[-LAST_TEST_EDITS_MAX:]

    if state.mode == "strict":
        entry = {"tool": tool_name}

        if tool_name == "Bash" and command:
            was_test = is_test_command(command)
            was_query = is_real_system_query(command)
            entry["was_test"] = was_test
            entry["command"] = command
            if was_test:
                entry["failed"] = is_test_failure(tool_result)
            if was_query:
                entry["was_query"] = True
                state.exchanges_since_query = 0
                state.slabs_without_data = 0
                state.has_queried_this_slab = True
        elif tool_name in ("Edit", "Write"):
            entry["file_path"] = file_path
            entry["was_test"] = False
        else:
            entry["was_test"] = False

        state.last_tool_sequence.append(entry)

        if len(state.last_tool_sequence) > MAX_TOOL_SEQUENCE_LENGTH:
            state.last_tool_sequence = state.last_tool_sequence[
                -MAX_TOOL_SEQUENCE_LENGTH:
            ]

        if tool_name in ("Edit", "Write") and not is_test_file(file_path):
            if detect_patch_forward(state.last_tool_sequence):
                state.patch_forward_count += 1

        if tool_name == "Skill":
            if not state.has_queried_this_slab:
                state.slabs_without_data += 1
            state.has_queried_this_slab = False

    return state


def handle_post_compact(state: SessionState) -> tuple:
    """Handle PostCompact event. Context was compressed — trigger auto-handoff."""
    state.compactions += 1

    stop_reason = (
        f"Context compacted ({state.compactions} time(s)) "
        f"— context window is full"
    )
    trigger_auto_handoff(state, stop_reason)
    state.stopped = 2

    response = (
        "CONTEXT COMPACTED: Context window was compressed by Claude Code. "
        "HANDOFF.md has been written automatically by the hook. "
        "Finish your current task, then write HANDOFF.md."
    )
    return state, response


def handle_pre_tool_use(
    state: SessionState,
    tool_name: str,
    file_path: str,
    command: str,
) -> tuple:
    """Handle PreToolUse: path protection + session limits. Returns (state, msg, blocked)."""
    state.tool_calls += 1

    blocked, block_msg = check_protected_paths(
        state, tool_name, file_path, command
    )
    if blocked:
        return state, block_msg, True

    state, response = apply_session_limits(state)
    return state, response, False


def parse_input(raw_input: str) -> dict:
    """Parse JSON input from Claude Code hook system."""
    try:
        return json.loads(raw_input)
    except json.JSONDecodeError:
        return {}


def main() -> int:
    """Read event from stdin, dispatch to handler, output JSON response."""
    raw_input = sys.stdin.read()
    event = parse_input(raw_input)

    if not event:
        return 0

    state_file = Path(SESSION_DIR) / STATE_FILENAME

    hook_event = event.get("hook_event_name", "")
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    tool_result = event.get("tool_result", "")

    file_path = tool_input.get("file_path", "") if isinstance(tool_input, dict) else ""
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

    state = load_state(state_file)

    response = ""
    blocked = False

    if hook_event == "UserPromptSubmit":
        state, response = handle_user_prompt(state)

    elif hook_event == "PostToolUse":
        result_text = tool_result if isinstance(tool_result, str) else json.dumps(tool_result)
        state = handle_post_tool_use(
            state, result_text,
            tool_name=tool_name, command=command, file_path=file_path,
        )

    elif hook_event == "PostCompact":
        state, response = handle_post_compact(state)

    elif hook_event == "PreToolUse":
        state, response, blocked = handle_pre_tool_use(
            state, tool_name, file_path, command
        )

    elif "prompt" in event:
        state, response = handle_user_prompt(state)

    elif tool_name:
        state, response, blocked = handle_pre_tool_use(
            state, tool_name, file_path, command
        )

    save_state(state, state_file)

    if response:
        event_name = hook_event or ("PreToolUse" if tool_name else "UserPromptSubmit")
        print(make_hook_response(event_name, response))

    return 2 if blocked else 0


# Re-export for tests and session_init
__all__ = [
    "DRIFT_CHECK_INTERVAL",
    "FALLBACK_MAX_EXCHANGES",
    "GRACE_TOOL_CALLS",
    "HARD_THRESHOLD_BYTES",
    "WARN_THRESHOLD_BYTES",
    "SessionState",
    "check_gates_blocked",
    "check_reports_blocked",
    "check_session_blocked",
    "check_thresholds",
    "handle_post_compact",
    "handle_post_tool_use",
    "handle_pre_tool_use",
    "handle_user_prompt",
    "load_state",
    "make_hook_response",
    "save_state",
    "should_warn",
]


if __name__ == "__main__":
    sys.exit(main())
