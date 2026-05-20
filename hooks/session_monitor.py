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
import re
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# --- Configuration ---

WARN_THRESHOLD_BYTES = 500_000  # ~70% of 200K token window → warning
HARD_THRESHOLD_BYTES = 700_000  # ~85% → handoff trigger
FALLBACK_MAX_EXCHANGES = 30  # Raised from 20
GRACE_TOOL_CALLS = 10  # Tool calls allowed after stop triggers

SESSION_DIR = ".session"
STATE_FILENAME = "state.json"

# Bash commands that write to files
BASH_WRITE_PATTERNS = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir)"
    r".*\.session"
)
BASH_SESSION_REF = re.compile(r"\.session(/|\s|$)")


@dataclass
class SessionState:
    session_start: int
    exchanges: int = 0
    tool_calls: int = 0
    cumulative_output_bytes: int = 0
    compactions: int = 0
    warned: bool = False
    stopped: int = 0  # 0=running, 1=grace, 2=hard-stop
    stop_at_tool_call: int = 0


def load_state(state_file: Path) -> SessionState:
    """Load session state from JSON file. Returns fresh state if missing/corrupt."""
    if not state_file.exists():
        return SessionState(session_start=int(time.time()))
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return SessionState(**data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return SessionState(session_start=int(time.time()))


def save_state(state: SessionState, state_file: Path) -> None:
    """Atomic save — write to temp file then rename."""
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=str(state_file.parent), suffix=".tmp"
    )
    try:
        with open(temp_fd, "w", encoding="utf-8") as temp_file:
            json.dump(asdict(state), temp_file, indent=2)
            temp_file.write("\n")
        Path(temp_path).replace(state_file)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise


def make_hook_response(event_name: str, context: str) -> str:
    """Build the JSON response expected by Claude Code hooks."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": event_name,
                "additionalContext": context,
            }
        }
    )


def check_thresholds(state: SessionState) -> tuple:
    """Check if any hard-stop threshold is met.

    Returns (triggered: bool, reason: str).
    Priority: compaction > bytes > exchanges.
    """
    if state.compactions >= 1:
        return True, (
            f"Context compacted ({state.compactions} time(s)) "
            f"— context window is full"
        )

    if state.cumulative_output_bytes > HARD_THRESHOLD_BYTES:
        return True, (
            f"Cumulative output bytes ({state.cumulative_output_bytes:,}) "
            f"exceeded threshold ({HARD_THRESHOLD_BYTES:,})"
        )

    if state.exchanges >= FALLBACK_MAX_EXCHANGES:
        return True, (
            f"Exchange limit reached "
            f"({state.exchanges}/{FALLBACK_MAX_EXCHANGES})"
        )

    return False, ""


def should_warn(state: SessionState) -> bool:
    """Check if we should emit a warning (approaching limits)."""
    if state.warned:
        return False
    if state.cumulative_output_bytes > WARN_THRESHOLD_BYTES:
        return True
    # Warn at ~75% of fallback exchange limit
    if state.exchanges >= int(FALLBACK_MAX_EXCHANGES * 0.75):
        return True
    return False


def check_session_blocked(
    tool_name: str, file_path: str, command: str
) -> tuple:
    """G-SESSION-1: Block agent writes to .session/ directory.

    Returns (blocked: bool, message: str).
    """
    if tool_name in ("Write", "Edit"):
        if ".session/" in file_path or file_path.endswith(".session"):
            return True, (
                "BLOCKED: Agent must not modify .session/ files "
                "(G-SESSION-1). Session state is managed by hooks only."
            )
        return False, ""

    if tool_name == "Bash" and command:
        if BASH_SESSION_REF.search(command):
            if BASH_WRITE_PATTERNS.search(command):
                return True, (
                    "BLOCKED: Agent must not modify .session/ files "
                    "(G-SESSION-1). Session state is managed by hooks only."
                )
            # Allow reads (cat, head, tail, ls, etc.)
            if ">" in command and ".session" in command:
                return True, (
                    "BLOCKED: Agent must not modify .session/ files "
                    "(G-SESSION-1). Session state is managed by hooks only."
                )
        return False, ""

    return False, ""


def is_handoff_allowed(tool_name: str, file_path: str, command: str) -> bool:
    """During hard stop, only handoff operations are allowed."""
    if tool_name in ("Write", "Edit"):
        return "HANDOFF.md" in file_path or "project-state.md" in file_path

    if tool_name == "Bash":
        allowed_prefixes = (
            "git commit",
            "git add",
            "git status",
            "git diff",
            "git log",
            "git stash",
            "mkdir",
        )
        return any(command.strip().startswith(prefix) for prefix in allowed_prefixes)

    return False


# --- Event handlers ---


def handle_user_prompt(state: SessionState) -> tuple:
    """Handle UserPromptSubmit event. Increments exchanges, checks warn."""
    state.exchanges += 1

    response = None
    if should_warn(state):
        state.warned = True
        response = (
            f"SESSION WARNING: {state.exchanges}/{FALLBACK_MAX_EXCHANGES} exchanges, "
            f"{state.cumulative_output_bytes:,}/{HARD_THRESHOLD_BYTES:,} bytes. "
            f"Context pressure building. Finish current work, commit, "
            f"and prepare HANDOFF.md. Do not start new slabs or features."
        )

    return state, response


def handle_post_tool_use(state: SessionState, tool_result: str) -> SessionState:
    """Handle PostToolUse event. Tracks cumulative output bytes."""
    state.cumulative_output_bytes += len(tool_result)
    return state


def handle_post_compact(state: SessionState) -> tuple:
    """Handle PostCompact event. Context was compressed — trigger handoff."""
    state.compactions += 1
    response = (
        "CONTEXT COMPACTED: Context window was compressed by Claude Code. "
        "This means context pressure is critical. "
        "Finish your current task, then IMMEDIATELY write HANDOFF.md "
        "and commit. The auto-continuation wrapper will relaunch a fresh session."
    )
    return state, response


def handle_pre_tool_use(
    state: SessionState,
    tool_name: str,
    file_path: str,
    command: str,
) -> tuple:
    """Handle PreToolUse event. Enforces limits + G-SESSION-1.

    Returns (state, response_message, blocked: bool).
    """
    state.tool_calls += 1

    # G-SESSION-1: block writes to .session/
    blocked, block_msg = check_session_blocked(tool_name, file_path, command)
    if blocked:
        return state, block_msg, True

    # Check hard-stop thresholds
    triggered, stop_reason = check_thresholds(state)

    if triggered:
        # First time hitting threshold → start grace period
        if state.stopped == 0:
            state.stopped = 1
            state.stop_at_tool_call = state.tool_calls + GRACE_TOOL_CALLS
            response = (
                f"SESSION LIMIT REACHED: {stop_reason}. "
                f"You have {GRACE_TOOL_CALLS} tool calls remaining to wrap up.\n\n"
                f"Finish your current task, then IMMEDIATELY:\n"
                f"1. Write HANDOFF.md — current status, what's done (commits), "
                f"what's next (spec text copied, not summarized), decisions, "
                f"code change plan for next slab\n"
                f"2. Update project-state.md Resume section\n"
                f"3. git add + git commit all work\n"
                f"4. Tell user: 'Session limit reached. "
                f"Start a new session — I will read HANDOFF.md to continue.'\n\n"
                f"Do NOT start new tasks. Wrap up and hand off."
            )
            return state, response, False  # Allow — grace period

        # Grace period active — check if exhausted
        grace_remaining = state.stop_at_tool_call - state.tool_calls
        if grace_remaining <= 0:
            # Hard stop — only handoff operations allowed
            if is_handoff_allowed(tool_name, file_path, command):
                state.stopped = 2
                return state, "", False

            state.stopped = 2
            response = (
                f"HARD STOP: Grace period exhausted. {stop_reason}.\n\n"
                f"ONLY allowed operations: Write HANDOFF.md, "
                f"update project-state.md, git commit.\n"
                f"Everything else is blocked. Write the handoff NOW "
                f"and tell the user to start a new session."
            )
            return state, response, True
        else:
            # Still in grace — remind but allow
            response = (
                f"SESSION LIMIT: {grace_remaining} tool calls remaining "
                f"before hard stop. Finish current work and write HANDOFF.md."
            )
            return state, response, False

    # Check warn thresholds (not triggered yet, but approaching)
    if should_warn(state) and not state.warned:
        state.warned = True
        response = (
            f"SESSION WARNING: {state.exchanges}/{FALLBACK_MAX_EXCHANGES} exchanges, "
            f"{state.cumulative_output_bytes:,}/{HARD_THRESHOLD_BYTES:,} bytes. "
            f"You are approaching the hard stop. Finish current work, commit, "
            f"and prepare HANDOFF.md. Do not start new slabs or features."
        )
        return state, response, False

    return state, "", False


# --- Main entry point ---


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

    # Determine state file location
    state_file = Path(SESSION_DIR) / STATE_FILENAME

    # Detect event type
    hook_event = event.get("hook_event_name", "")
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})
    tool_result = event.get("tool_result", "")

    file_path = tool_input.get("file_path", "") if isinstance(tool_input, dict) else ""
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

    # Load state
    state = load_state(state_file)

    response = ""
    blocked = False

    if hook_event == "UserPromptSubmit":
        state, response = handle_user_prompt(state)

    elif hook_event == "PostToolUse":
        result_text = tool_result if isinstance(tool_result, str) else json.dumps(tool_result)
        state = handle_post_tool_use(state, result_text)

    elif hook_event == "PostCompact":
        state, response = handle_post_compact(state)

    elif hook_event == "PreToolUse":
        state, response, blocked = handle_pre_tool_use(
            state, tool_name, file_path, command
        )

    # Detect event name for prompt if present
    elif "prompt" in event:
        state, response = handle_user_prompt(state)

    else:
        # Unknown event — check if it's a tool use by presence of tool_name
        if tool_name:
            state, response, blocked = handle_pre_tool_use(
                state, tool_name, file_path, command
            )

    # Save state
    save_state(state, state_file)

    # Output response
    if response:
        event_name = hook_event or ("PreToolUse" if tool_name else "UserPromptSubmit")
        print(make_hook_response(event_name, response))

    return 2 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
