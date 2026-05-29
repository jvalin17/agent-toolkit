"""Session limit enforcement.

continue_mode=True: write HANDOFF.md and launch a new session.
continue_mode=False: warn only, session continues through compaction.
"""

from auto_handoff import trigger_auto_handoff
from session_state import (
    FALLBACK_MAX_EXCHANGES,
    HARD_THRESHOLD_BYTES,
    SessionState,
    check_thresholds,
    should_warn,
)


def apply_session_limits(state: SessionState) -> tuple:
    """Apply byte/time limits. Returns (state, response_message).

    continue_mode=True: writes HANDOFF.md and launches new claude session.
    continue_mode=False: warns only, session continues through compaction.
    """
    triggered, stop_reason = check_thresholds(state)

    if triggered and state.continue_mode and not state.warned:
        state.warned = True
        trigger_auto_handoff(state, stop_reason)
        return state, (
            f"SESSION LIMIT: {stop_reason}. "
            f"HANDOFF.md written. A new session is being launched. "
            f"Wrap up current work."
        )

    if triggered and not state.warned:
        state.warned = True
        return state, (
            f"SESSION LIMIT: {stop_reason}. "
            f"The session continues (compaction handles context pressure). "
            f"Quality may degrade. Wrap up current work."
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
