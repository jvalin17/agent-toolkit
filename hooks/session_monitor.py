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

# Real-system query patterns (strict mode drift detection)
REAL_SYSTEM_QUERY_PATTERNS = re.compile(
    r"\b(curl|wget|httpie|grpcurl|postman)\b"
    r"|\bhttp\s+(GET|POST|PUT|DELETE|PATCH)\b"
    r"|\b(psql|mysql|sqlite3|mongosh)\b"
    r"|\b(SELECT|INSERT|UPDATE|DELETE)\s+"
    r"|\bdocker\s+exec\b.*\b(psql|mysql|mongo|redis)",
    re.IGNORECASE,
)

# Test runner patterns
TEST_RUNNER_PATTERNS = re.compile(
    r"\b(pytest|py\.test|python3?\s+-m\s+pytest)\b"
    r"|\b(jest|vitest|mocha)\b"
    r"|\bgo\s+test\b"
    r"|\bcargo\s+test\b"
    r"|\bnpm\s+(run\s+)?test\b"
    r"|\byarn\s+test\b",
    re.IGNORECASE,
)

# Test failure indicators in output
TEST_FAILURE_PATTERNS = re.compile(
    r"\bFAILED\b|\bFAILURE\b|\bERROR\b.*test"
    r"|\bfailed\b.*\btests?\b"
    r"|\bAssertionError\b"
    r"|\bExpect.*received\b",
    re.IGNORECASE,
)

MAX_TOOL_SEQUENCE_LENGTH = 10
DRIFT_CHECK_INTERVAL = 15  # Integrity check every N exchanges in strict mode


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
        return SessionState(**filtered)
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


# --- Drift detection (strict mode) ---


def is_real_system_query(command: str) -> bool:
    """Check if a Bash command is a real-system query (curl, psql, SELECT, etc.)."""
    if not command:
        return False
    return bool(REAL_SYSTEM_QUERY_PATTERNS.search(command))


def is_test_command(command: str) -> bool:
    """Check if a Bash command runs a test suite."""
    if not command:
        return False
    return bool(TEST_RUNNER_PATTERNS.search(command))


def is_test_failure(output: str) -> bool:
    """Check if tool output indicates test failure."""
    if not output:
        return False
    return bool(TEST_FAILURE_PATTERNS.search(output))


def is_test_file(file_path: str) -> bool:
    """Check if a file path is a test file."""
    if not file_path:
        return False
    name = Path(file_path).name
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".test.js")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.js")
        or "/tests/" in file_path
        or "/test/" in file_path
        or "/__tests__/" in file_path
    )


def detect_patch_forward(sequence: list) -> bool:
    """Detect patch-forward pattern in tool sequence.

    Pattern: test failure → Edit/Write source file with no investigation between.
    Investigation = Read, Grep, or real-system query (Bash with query pattern).
    """
    if len(sequence) < 2:
        return False

    # Walk backward from the last entry
    last = sequence[-1]
    if last.get("tool") not in ("Edit", "Write"):
        return False

    # If editing a test file, not patch-forward
    if is_test_file(last.get("file_path", "")):
        return False

    # Look backward for test failure, checking for investigation between
    for i in range(len(sequence) - 2, -1, -1):
        entry = sequence[i]

        # Found investigation — not patch-forward
        if entry.get("tool") in ("Read", "Grep"):
            return False
        if entry.get("was_query"):
            return False

        # Found test failure — this is patch-forward
        if entry.get("was_test") and entry.get("failed"):
            return True

        # Found non-test, non-investigation tool — stop searching
        # (the test failure must be adjacent-ish)
        if entry.get("tool") not in ("Edit", "Write"):
            return False

    return False


def compute_drift_score(
    exchanges_since_query: int,
    patch_forward_count: int,
    slabs_without_data: int,
) -> float:
    """Compute drift score from counters. Returns 0.0 to 1.0.

    Formula from requirements/strict-mode.md:
      min(exchanges/10, 1.0) * 0.4 + min(patches/3, 1.0) * 0.4 + min(slabs/2, 1.0) * 0.2
    """
    return (
        min(exchanges_since_query / 10, 1.0) * 0.4
        + min(patch_forward_count / 3, 1.0) * 0.4
        + min(slabs_without_data / 2, 1.0) * 0.2
    )


# --- Event handlers ---


def handle_user_prompt(state: SessionState) -> tuple:
    """Handle UserPromptSubmit event. Increments exchanges, checks warn."""
    state.exchanges += 1

    # Strict mode: track exchanges since last real-system query
    if state.mode == "strict":
        state.exchanges_since_query += 1

    response = None

    # Strict mode: periodic integrity check
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

    if should_warn(state):
        state.warned = True
        response = (
            f"SESSION WARNING: {state.exchanges}/{FALLBACK_MAX_EXCHANGES} exchanges, "
            f"{state.cumulative_output_bytes:,}/{HARD_THRESHOLD_BYTES:,} bytes. "
            f"Context pressure building. Finish current work, commit, "
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
