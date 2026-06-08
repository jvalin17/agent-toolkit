"""Session limit enforcement — two-layer system.

Layer 1 (compact_at_minutes, default 70): Write HANDOFF.md breadcrumb,
session continues through compaction. No restart needed.

Layer 2 (max_session_minutes, default 200): Hard stop. Write final
HANDOFF.md with restart prompt for the user to paste into new session.
"""

from auto_handoff import trigger_auto_handoff, write_auto_handoff, get_git_log
from pathlib import Path
from session_state import (
    FALLBACK_MAX_EXCHANGES,
    HARD_THRESHOLD_BYTES,
    SessionState,
    check_compact_threshold,
    check_thresholds,
    should_warn,
)


RESTART_PROMPT_TEMPLATE = """

## Restart Prompt

Copy-paste the following into your next Claude session to continue seamlessly:

---

Read HANDOFF.md first. You are continuing a multi-session task. The previous session hit its time/context limit. Pick up exactly where it left off:
1. Read HANDOFF.md for goal, progress, and next steps
2. Read project-state.md for overall project context
3. Continue the work — do NOT re-do completed items listed above

---
"""


def _write_breadcrumb_handoff(state: SessionState, reason: str) -> None:
    """Layer 1: Write HANDOFF.md as a breadcrumb. Session continues."""
    handoff_path = Path("HANDOFF.md")
    previous = ""
    if handoff_path.exists():
        try:
            previous = handoff_path.read_text(encoding="utf-8")
        except OSError:
            pass

    git_log = get_git_log()
    write_auto_handoff(
        handoff_path=handoff_path,
        state=state,
        stop_reason=f"[BREADCRUMB] {reason}",
        previous_handoff=previous,
        git_log=git_log,
    )


def _write_final_handoff(state: SessionState, reason: str) -> None:
    """Layer 2: Write final HANDOFF.md with restart prompt."""
    handoff_path = Path("HANDOFF.md")
    previous = ""
    if handoff_path.exists():
        try:
            previous = handoff_path.read_text(encoding="utf-8")
        except OSError:
            pass

    git_log = get_git_log()
    write_auto_handoff(
        handoff_path=handoff_path,
        state=state,
        stop_reason=f"[HARD STOP] {reason}",
        previous_handoff=previous,
        git_log=git_log,
    )

    # Append restart prompt to HANDOFF.md
    content = handoff_path.read_text(encoding="utf-8")
    handoff_path.write_text(content + RESTART_PROMPT_TEMPLATE, encoding="utf-8")


def apply_session_limits(state: SessionState) -> tuple:
    """Apply two-layer time/byte limits. Returns (state, response_message).

    Layer 1 (compact_at): Write breadcrumb HANDOFF.md, session continues.
    Layer 2 (max_session_minutes): Hard stop with restart prompt.
    """
    # --- Layer 2: Hard stop ---
    triggered, stop_reason = check_thresholds(state)

    if triggered and state.stopped == 0:
        state.stopped = 2
        _write_final_handoff(state, stop_reason)
        return state, (
            f"SESSION HARD STOP: {stop_reason}.\n\n"
            f"HANDOFF.md has been written with a restart prompt.\n"
            f"This session can no longer make meaningful progress.\n\n"
            f"To continue, start a new session and paste:\n"
            f"  \"Read HANDOFF.md first. You are continuing a multi-session task.\"\n\n"
            f"Or run: python3 scripts/auto_continue.py"
        )

    # --- Layer 1: Breadcrumb (write HANDOFF.md, keep going) ---
    compact_triggered, compact_reason = check_compact_threshold(state)

    if compact_triggered and not state.warned:
        state.warned = True
        _write_breadcrumb_handoff(state, compact_reason)
        return state, (
            f"SESSION CHECKPOINT ({compact_reason}): "
            f"HANDOFF.md updated as a breadcrumb in case of crash/compaction. "
            f"Session continues — no restart needed. "
            f"After compaction, re-read HANDOFF.md to re-orient."
        )

    # --- Warning (approaching limits) ---
    if should_warn(state) and not state.warned:
        state.warned = True
        return state, (
            f"SESSION WARNING: {state.exchanges}/{FALLBACK_MAX_EXCHANGES} exchanges, "
            f"{state.cumulative_output_bytes:,}/{HARD_THRESHOLD_BYTES:,} bytes. "
            f"Approaching session limit. Finish current work "
            f"and do not start new slabs or features."
        )

    return state, ""
