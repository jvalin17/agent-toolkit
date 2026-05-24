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

from auto_handoff import (
    parse_handoff_header,
    trigger_auto_handoff,
    write_auto_handoff,
)
from strict_mode import (
    compute_drift_score,
    detect_patch_forward,
    is_real_system_query,
    is_test_command,
    is_test_failure,
    is_test_file,
)

# --- Configuration ---

WARN_THRESHOLD_BYTES = 500_000  # ~70% of 200K token window → warning
HARD_THRESHOLD_BYTES = 700_000  # ~85% → handoff trigger
FALLBACK_MAX_EXCHANGES = 30  # Raised from 20
GRACE_TOOL_CALLS = 10  # Tool calls allowed after stop triggers
DEFAULT_MAX_SESSION_MINUTES = 0  # Time-based hard stop (0 = disabled, set in gates.json)

SESSION_DIR = ".session"
STATE_FILENAME = "state.json"

# Bash commands that write to files
BASH_WRITE_PATTERNS = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir)"
    r".*\.session"
)
BASH_SESSION_REF = re.compile(r"\.session(/|\s|$)")

# .gates/ protection patterns
BASH_GATES_WRITE = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir)"
    r".*\.gates"
)
BASH_GATES_REF = re.compile(r"\.gates(/|\s|$)")

# reports/ protection patterns (G-REPORT-1)
BASH_REPORTS_WRITE = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir|cat\s*<<|printf)"
    r".*\breports(/|\b)"
)
BASH_REPORTS_REF = re.compile(r"\breports(/|\s|$)")

MAX_TOOL_SEQUENCE_LENGTH = 10
DRIFT_CHECK_INTERVAL = 15  # Integrity check every N exchanges in strict mode

# Per-counter warning thresholds (strict mode)
EXCHANGES_WARN_THRESHOLD = 10
PATCH_FORWARD_WARN_THRESHOLD = 2
SLABS_WITHOUT_DATA_WARN_THRESHOLD = 1


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
    # Strict mode drift tracking
    mode: str = "normal"
    exchanges_since_query: int = 0
    patch_forward_count: int = 0
    slabs_without_data: int = 0
    last_tool_sequence: list = field(default_factory=list)
    has_queried_this_slab: bool = False
    max_session_minutes: int = 0  # 0 = disabled, set via gates.json
    gate_protect: bool = False  # G-GATE-1: block agent writes to .gates/
    report_protect: bool = True  # G-REPORT-1: block agent writes to reports/


def load_state(state_file: Path) -> SessionState:
    """Load session state from JSON file. Returns fresh state if missing/corrupt.

    Tolerates missing fields (uses defaults) and extra fields (ignores them)
    for backward/forward compatibility when SessionState gains new fields.
    """
    if not state_file.exists():
        return SessionState(session_start=int(time.time()))
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        # Filter to only known fields for forward compatibility
        valid_fields = {f.name for f in SessionState.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        state = SessionState(**filtered)
        # Self-heal stale session_start (e.g. session_init didn't run)
        if state.max_session_minutes > 0:
            elapsed = int(time.time()) - state.session_start
            if elapsed > state.max_session_minutes * 60 * 2:
                state.session_start = int(time.time())
        return state
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
    Priority: compaction > time > bytes.
    """
    if state.compactions >= 1:
        return True, (
            f"Context compacted ({state.compactions} time(s)) "
            f"— context window is full"
        )

    if state.max_session_minutes > 0:
        elapsed_seconds = int(time.time()) - state.session_start
        elapsed_minutes = elapsed_seconds / 60
        if elapsed_minutes >= state.max_session_minutes:
            return True, (
                f"Session time ({int(elapsed_minutes)} minutes) "
                f"exceeded limit ({state.max_session_minutes} minutes)"
            )

    if state.cumulative_output_bytes > HARD_THRESHOLD_BYTES:
        return True, (
            f"Cumulative output bytes ({state.cumulative_output_bytes:,}) "
            f"exceeded threshold ({HARD_THRESHOLD_BYTES:,})"
        )

    return False, ""


def should_warn(state: SessionState) -> bool:
    """Check if we should emit a warning (approaching limits).

    Only bytes and compaction matter — exchange count is tracked
    for diagnostics but never triggers warnings or hard stops.
    """
    if state.warned:
        return False
    if state.cumulative_output_bytes > WARN_THRESHOLD_BYTES:
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


def check_gates_blocked(
    tool_name: str, file_path: str, command: str
) -> tuple:
    """G-GATE-1: Block agent writes to .gates/ directory.

    Prevents agents from forging gate files (echo READY > .gates/precommit-passed).
    Only skill hooks should write gate files. Activated via gate_protect in gates.json.

    Returns (blocked: bool, message: str).
    """
    if tool_name in ("Write", "Edit"):
        if ".gates/" in file_path or file_path.endswith(".gates"):
            return True, (
                "BLOCKED: Agent must not modify .gates/ files "
                "(G-GATE-1). Gate files are written by skill hooks only."
            )
        return False, ""

    if tool_name == "Bash" and command:
        if BASH_GATES_REF.search(command):
            if BASH_GATES_WRITE.search(command):
                return True, (
                    "BLOCKED: Agent must not modify .gates/ files "
                    "(G-GATE-1). Gate files are written by skill hooks only."
                )
            if ">" in command and ".gates" in command:
                return True, (
                    "BLOCKED: Agent must not modify .gates/ files "
                    "(G-GATE-1). Gate files are written by skill hooks only."
                )
        return False, ""

    return False, ""


def check_reports_blocked(
    tool_name: str, file_path: str, command: str
) -> tuple:
    """G-REPORT-1: Block agent writes to reports/ directory.

    Prevents agents from forging skill reports directly (Write tool or shell
    redirection like `echo "READY" > reports/precommit/pc_x.md`). Reports are
    the toolkit's source of truth — they must be produced by skill hooks, not
    by free-form agent output. Activated via report_protect in gates.json.

    Returns (blocked: bool, message: str).
    """
    msg = (
        "BLOCKED: Agent must not write to reports/ "
        "(G-REPORT-1). Reports are produced by skill hooks only."
    )

    if tool_name in ("Write", "Edit"):
        # Match reports/, ./reports/, /path/to/reports/, anywhere in path.
        if "reports/" in file_path or file_path.rstrip("/").endswith("/reports"):
            return True, msg
        return False, ""

    if tool_name == "Bash" and command:
        if BASH_REPORTS_REF.search(command):
            if BASH_REPORTS_WRITE.search(command):
                return True, msg
            # Catch generic redirection into reports/
            if (">" in command or ">>" in command) and "reports" in command:
                return True, msg
        return False, ""

    return False, ""


# --- Drift detection + auto-handoff: imported from strict_mode.py, auto_handoff.py ---



# --- Event handlers ---


def handle_user_prompt(state: SessionState) -> tuple:
    """Handle UserPromptSubmit event. Increments exchanges, checks warn."""
    state.exchanges += 1

    # Strict mode: track exchanges since last real-system query
    if state.mode == "strict":
        state.exchanges_since_query += 1

    response = None

    # Strict mode: periodic integrity check (takes priority over per-counter)
    if (
        state.mode == "strict"
        and state.exchanges % DRIFT_CHECK_INTERVAL == 0
    ):
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

        return state, response

    # Strict mode: per-counter threshold warnings (between integrity checks)
    if state.mode == "strict":
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
            response = "STRICT MODE WARNING:\n- " + "\n- ".join(warnings)
            return state, response

    if should_warn(state):
        state.warned = True
        response = (
            f"SESSION WARNING: {state.exchanges}/{FALLBACK_MAX_EXCHANGES} exchanges, "
            f"{state.cumulative_output_bytes:,}/{HARD_THRESHOLD_BYTES:,} bytes. "
            f"Context pressure building. Finish the current safe stopping point "
            f"and prepare HANDOFF.md. Do not start new slabs or features."
        )

    return state, response


def handle_post_tool_use(
    state: SessionState,
    tool_result: str,
    tool_name: str = "",
    command: str = "",
    file_path: str = "",
) -> SessionState:
    """Handle PostToolUse event. Tracks cumulative output bytes and drift."""
    state.cumulative_output_bytes += len(tool_result)

    # Strict mode: track tool sequence and drift counters
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

        # Cap sequence length
        if len(state.last_tool_sequence) > MAX_TOOL_SEQUENCE_LENGTH:
            state.last_tool_sequence = state.last_tool_sequence[
                -MAX_TOOL_SEQUENCE_LENGTH:
            ]

        # Check for patch-forward pattern
        if tool_name in ("Edit", "Write") and not is_test_file(file_path):
            if detect_patch_forward(state.last_tool_sequence):
                state.patch_forward_count += 1

        # Slab boundary: Skill tool (precommit signals slab completion)
        if tool_name == "Skill":
            if not state.has_queried_this_slab:
                state.slabs_without_data += 1
            state.has_queried_this_slab = False

    return state


def handle_post_compact(state: SessionState) -> tuple:
    """Handle PostCompact event. Context was compressed — trigger auto-handoff."""
    state.compactions += 1

    # Compaction = immediate hard stop. Hook writes HANDOFF.md.
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
    """Handle PreToolUse event. Enforces limits + G-SESSION-1.

    Returns (state, response_message, blocked: bool).
    """
    state.tool_calls += 1

    # G-SESSION-1: block writes to .session/
    blocked, block_msg = check_session_blocked(tool_name, file_path, command)
    if blocked:
        return state, block_msg, True

    # G-GATE-1: block writes to .gates/ (when gate_protect is on)
    if state.gate_protect:
        blocked, block_msg = check_gates_blocked(tool_name, file_path, command)
        if blocked:
            return state, block_msg, True

    # G-REPORT-1: block writes to reports/ (when report_protect is on)
    if state.report_protect:
        blocked, block_msg = check_reports_blocked(tool_name, file_path, command)
        if blocked:
            return state, block_msg, True

    # Check hard-stop thresholds
    triggered, stop_reason = check_thresholds(state)

    if triggered:
        is_time_triggered = "minutes" in stop_reason

        # Time-based limit: immediate hard stop, no grace period
        if is_time_triggered and state.stopped < 2:
            state.stopped = 2
            trigger_auto_handoff(state, stop_reason)

            response = (
                f"SESSION TIME LIMIT: {stop_reason}.\n\n"
                f"HANDOFF.md has been written automatically by the hook.\n"
                f"The auto-continuation wrapper will relaunch a fresh session.\n"
                f"Finish your current task, then write HANDOFF.md."
            )
            return state, response, False

        # Other limits: first time hitting threshold → start grace period
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
                f"3. Tell user: 'Session limit reached. "
                f"Start a new session — it will read HANDOFF.md to continue.'\n\n"
                f"Do NOT start new tasks. Finish current task and hand off."
            )
            return state, response, False  # Allow — grace period

        # Grace period active — check if exhausted
        grace_remaining = state.stop_at_tool_call - state.tool_calls
        if grace_remaining <= 0:
            # Hard stop — hook writes the handoff automatically
            if state.stopped != 2:
                # First transition to hard stop — write handoff
                state.stopped = 2
                trigger_auto_handoff(state, stop_reason)

            response = (
                f"HARD STOP: Grace period exhausted. {stop_reason}.\n\n"
                f"HANDOFF.md has been written automatically by the hook.\n"
                f"Finish your current task, then write HANDOFF.md."
            )
            return state, response, False
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
            f"You are approaching the session limit. Finish current work "
            f"and do not start new slabs or features."
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
