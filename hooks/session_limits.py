"""Session limit enforcement (grace period, handoff triggers) for PreToolUse."""

from auto_handoff import trigger_auto_handoff
from session_state import (
    FALLBACK_MAX_EXCHANGES,
    GRACE_TOOL_CALLS,
    HARD_THRESHOLD_BYTES,
    SessionState,
    check_thresholds,
    should_warn,
)


def apply_session_limits(state: SessionState) -> tuple:
    """Apply byte/time/compaction limits. Returns (state, response_message)."""
    triggered, stop_reason = check_thresholds(state)
    if triggered:
        return _handle_limit_triggered(state, stop_reason)

    if should_warn(state) and not state.warned:
        state.warned = True
        response = (
            f"SESSION WARNING: {state.exchanges}/{FALLBACK_MAX_EXCHANGES} exchanges, "
            f"{state.cumulative_output_bytes:,}/{HARD_THRESHOLD_BYTES:,} bytes. "
            f"You are approaching the session limit. Finish current work "
            f"and do not start new slabs or features."
        )
        return state, response

    return state, ""


def _handle_limit_triggered(state: SessionState, stop_reason: str) -> tuple:
    is_time_triggered = "minutes" in stop_reason

    if is_time_triggered and state.stopped < 2:
        state.stopped = 2
        trigger_auto_handoff(state, stop_reason)
        return state, (
            f"SESSION TIME LIMIT: {stop_reason}.\n\n"
            f"HANDOFF.md has been written automatically by the hook.\n"
            f"The auto-continuation wrapper will relaunch a fresh session.\n"
            f"Finish your current task, then write HANDOFF.md."
        )

    if state.stopped == 0:
        state.stopped = 1
        state.stop_at_tool_call = state.tool_calls + GRACE_TOOL_CALLS
        return state, (
            f"SESSION LIMIT REACHED: {stop_reason}. "
            f"You have {GRACE_TOOL_CALLS} tool calls remaining to wrap up.\n\n"
            f"Finish your current task, then IMMEDIATELY:\n"
            f"1. Write HANDOFF.md — current status, what's done (commits), "
            f"what's next (spec text copied, not summarized), decisions, "
            f"code change plan for next slab\n"
            f"2. Update project-state.md Resume section\n"
            f"3. Tell user: 'Session limit reached. "
            f"Start a new session — it will read HANDOFF.md to continue.'\n\n"
            f"Do NOT start new tasks. Finish current task and hand off."
        )

    grace_remaining = state.stop_at_tool_call - state.tool_calls
    if grace_remaining <= 0:
        if state.stopped != 2:
            state.stopped = 2
            trigger_auto_handoff(state, stop_reason)
        return state, (
            f"HARD STOP: Grace period exhausted. {stop_reason}.\n\n"
            f"HANDOFF.md has been written automatically by the hook.\n"
            f"Finish your current task, then write HANDOFF.md."
        )

    return state, (
        f"SESSION LIMIT: {grace_remaining} tool calls remaining "
        f"before hard stop. Finish current work and write HANDOFF.md."
    )
