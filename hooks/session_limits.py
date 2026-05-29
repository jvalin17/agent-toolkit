"""Session limit enforcement — warn only, never stop.

Sessions continue through compaction. Limits produce warnings
so the agent prioritizes current work over starting new tasks.
No handoff, no stop, no restart — compaction handles context pressure.
"""

from session_state import (
    FALLBACK_MAX_EXCHANGES,
    HARD_THRESHOLD_BYTES,
    SessionState,
    check_thresholds,
    should_warn,
)


def apply_session_limits(state: SessionState) -> tuple:
    """Apply byte/time limits. Returns (state, response_message).

    Never stops the session. Warns once when thresholds are hit
    so the agent wraps up current work instead of starting new tasks.
    Compaction handles context pressure naturally.
    """
    triggered, stop_reason = check_thresholds(state)

    if triggered and not state.warned:
        state.warned = True
        return state, (
            f"SESSION LIMIT: {stop_reason}. "
            f"The session will continue (compaction handles context pressure). "
            f"Quality may degrade. Wrap up current work before starting new tasks."
        )

    if should_warn(state) and not state.warned:
        state.warned = True
        return state, (
            f"SESSION WARNING: {state.exchanges}/{FALLBACK_MAX_EXCHANGES} exchanges, "
            f"{state.cumulative_output_bytes:,}/{HARD_THRESHOLD_BYTES:,} bytes. "
            f"Approaching session limit. Finish current work "
            f"and do not start new slabs or features."
        )

    return state, ""
