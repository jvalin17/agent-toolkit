#!/usr/bin/env python3
"""Session monitor hook — context-based session limits.

Context-pressure detection:
- Cumulative tool output bytes (PostToolUse)
- Compaction events (SessionStart with source "compact")
- Exchange count fallback (raised threshold)

Single script, multiple events. Reads hook_event_name from stdin JSON
and dispatches to the appropriate handler.

Fires on: PreToolUse, PostToolUse, UserPromptSubmit, SessionStart (matcher "compact")
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
    check_compact_threshold,
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

# Retry loop detection
MAX_RECENT_ERRORS = 10  # keep last N errors
RETRY_LOOP_THRESHOLD = 3  # same error 3 times = stuck
ERROR_MATCH_LENGTH = 100  # compare first N chars of error message

# Damage radius
DAMAGE_RADIUS_WARN = 5  # warn after this many unique files edited
DAMAGE_RADIUS_BLOCK = 15  # block after this many (likely off track)

# Bash source-write detection
import re as _re_bash

_SOURCE_EXTENSIONS = (
    r"\.py|\.ts|\.tsx|\.js|\.jsx|\.go|\.rs|\.java|\.kt|\.swift"
    r"|\.c|\.cpp|\.h|\.rb|\.php|\.cs|\.scala|\.ex|\.exs"
)

# Patterns that indicate a Bash command writes to a source file
_BASH_WRITE_COMMANDS = _re_bash.compile(
    r"sed\s+-i"        # sed in-place edit
    r"|patch\b"        # patch command
)

_BASH_REDIRECT_TO_SOURCE = _re_bash.compile(
    r"(?:>|>>)\s*\S*(?:" + _SOURCE_EXTENSIONS + r")(?:\s|$|'|\")"
)

_BASH_FILE_COMMANDS_TO_SOURCE = _re_bash.compile(
    r"(?:tee|cp|mv)\s+\S*\s*\S*(?:" + _SOURCE_EXTENSIONS + r")(?:\s|$|'|\")"
)

# Exempt paths — writes here don't count as source edits
_BASH_EXEMPT_PATHS = _re_bash.compile(
    r"hooks/|scripts/|\.scratch/|\.session/|\.gates/|\.github/"
)


def _detect_bash_source_write(command: str) -> bool:
    """Detect if a Bash command writes to source files.

    Returns True if the command modifies source code files,
    bypassing Edit/Write tool protections.
    """
    if not command:
        return False

    # Git commands are not source writes
    if command.lstrip().startswith("git "):
        return False

    # Check for exempt paths in the command
    if _BASH_EXEMPT_PATHS.search(command):
        return False

    # patch always modifies source files
    if _re_bash.search(r"\bpatch\b", command):
        return True

    # sed -i targeting a source file
    if _re_bash.search(r"sed\s+-i", command):
        if _re_bash.search(_SOURCE_EXTENSIONS, command):
            return True

    # Redirect (> or >>) to a source file
    if _BASH_REDIRECT_TO_SOURCE.search(command):
        return True

    # cp/mv/tee to a source file
    if _BASH_FILE_COMMANDS_TO_SOURCE.search(command):
        return True

    return False


def _invalidate_precommit_on_bash(command: str, project_dir: Path) -> None:
    """Clear precommit-passed if Bash command writes to source files.

    Only in default/standard/safe modes.
    """
    if not _detect_bash_source_write(command):
        return

    try:
        from gate_hook import load_gate_config
        from mode_resolver import resolve_mode_from_config
        config = load_gate_config(project_dir)
        mode = resolve_mode_from_config(config)
        if mode.name not in ("default", "standard", "safe"):
            return

        flag = project_dir / ".gates" / "precommit-passed"
        if flag.is_file():
            flag.unlink()
    except (OSError, ImportError) as exc:
        # Never silent: a stale precommit flag that survives is a gate hole.
        sys.stderr.write(
            f"session_monitor: could not invalidate precommit after Bash source write: {exc}\n"
        )


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
            "\nCRITICAL DRIFT: Score exceeds 0.8. "
            "Query the real system before continuing. "
            "Quality is degrading."
        )
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


EDIT_FAILURE_PATTERNS = [
    "old_string was not found",
    "old_string is not unique",
    r"Found \d+ matches",
    "replace_all is false",
    "not found in the file",
    "File has not been read yet",
]

import re as _re
_EDIT_FAILURE_RE = _re.compile("|".join(EDIT_FAILURE_PATTERNS), _re.IGNORECASE)


def _check_edit_failure(tool_name: str, tool_result: str, file_path: str) -> Optional[str]:
    """Check if an Edit/Write tool call failed. Returns warning or None."""
    if tool_name not in ("Edit", "Write"):
        return None
    if not tool_result:
        return None
    if _EDIT_FAILURE_RE.search(tool_result):
        filename = Path(file_path).name if file_path else "unknown"
        return (
            f"Edit on {filename} did not apply — re-read the file and retry. "
            f"({tool_result[:150]})"
        )
    return None


EDIT_TOOLS = ("Edit", "Write")
BASH_ERROR_MARKERS = ("error", "traceback", "failed", "exit code")


def _resolved(path: str) -> str:
    return str(Path(path).resolve()) if path else ""


def _track_edit_failure(
    state: SessionState, tool_name: str, tool_result: str, file_path: str,
) -> Optional[str]:
    """Record a failed edit (blocks until the file is re-read); clear it on success/read."""
    edit_warning = _check_edit_failure(tool_name, tool_result, file_path)
    same_file = _resolved(state.pending_failed_edit) == _resolved(file_path)
    if edit_warning and file_path:
        state.pending_failed_edit = _resolved(file_path)
    elif file_path and same_file and (tool_name in EDIT_TOOLS or tool_name == "Read"):
        state.pending_failed_edit = ""
    return edit_warning


def _track_edited_files(state: SessionState, tool_name: str, file_path: str) -> None:
    """Recent test edits (TDD window) and unique files edited (damage radius)."""
    if tool_name not in EDIT_TOOLS or not file_path:
        return
    if is_test_file(file_path):
        state.last_test_edits.append(file_path)
        state.last_test_edits = state.last_test_edits[-LAST_TEST_EDITS_MAX:]
    resolved = _resolved(file_path)
    if resolved not in state.files_edited:
        state.files_edited.append(resolved)


def _track_bash_errors(state: SessionState, tool_name: str, tool_result: str) -> None:
    """Keep the last few Bash error signatures for retry-loop detection."""
    if tool_name != "Bash" or not tool_result:
        return
    result_lower = tool_result.lower()
    if any(marker in result_lower for marker in BASH_ERROR_MARKERS):
        state.recent_errors.append(tool_result.strip()[:ERROR_MATCH_LENGTH])
        state.recent_errors = state.recent_errors[-MAX_RECENT_ERRORS:]
    else:
        state.recent_errors = []  # success clears history — agent is making progress


def _strict_sequence_entry(
    state: SessionState, tool_name: str, command: str, tool_result: str, file_path: str,
) -> dict:
    entry: dict = {"tool": tool_name, "was_test": False}
    if tool_name == "Bash" and command:
        entry["command"] = command
        entry["was_test"] = is_test_command(command)
        if entry["was_test"]:
            entry["failed"] = is_test_failure(tool_result)
        if is_real_system_query(command):
            entry["was_query"] = True
            state.exchanges_since_query = 0
            state.slabs_without_data = 0
            state.has_queried_this_slab = True
    elif tool_name in EDIT_TOOLS:
        entry["file_path"] = file_path
    return entry


def _track_strict_mode(
    state: SessionState, tool_name: str, command: str, tool_result: str, file_path: str,
) -> None:
    """Strict mode: tool sequence, patch-forward and slabs-without-data drift signals."""
    state.last_tool_sequence.append(
        _strict_sequence_entry(state, tool_name, command, tool_result, file_path)
    )
    state.last_tool_sequence = state.last_tool_sequence[-MAX_TOOL_SEQUENCE_LENGTH:]

    if tool_name in EDIT_TOOLS and not is_test_file(file_path):
        if detect_patch_forward(state.last_tool_sequence):
            state.patch_forward_count += 1

    if tool_name == "Skill":
        if not state.has_queried_this_slab:
            state.slabs_without_data += 1
        state.has_queried_this_slab = False


def handle_post_tool_use(
    state: SessionState,
    tool_result: str,
    tool_name: str = "",
    command: str = "",
    file_path: str = "",
) -> tuple:
    """Handle PostToolUse event. Tracks bytes, edits, errors, and strict-mode drift."""
    state.cumulative_output_bytes += len(tool_result)
    edit_warning = _track_edit_failure(state, tool_name, tool_result, file_path)
    _track_edited_files(state, tool_name, file_path)
    _track_bash_errors(state, tool_name, tool_result)
    if state.mode == "strict":
        _track_strict_mode(state, tool_name, command, tool_result, file_path)
    return state, edit_warning


def handle_post_compact(state: SessionState) -> tuple:
    """Handle compaction (SessionStart/compact). Context was compressed — session continues.

    Compaction is normal. The session keeps running with compressed context.
    We just note it and warn that quality may degrade.
    """
    state.compactions += 1

    response = (
        f"CONTEXT COMPACTED ({state.compactions}x): Claude Code compressed the context. "
        f"The session continues. Quality may degrade with repeated compactions. "
        f"Consider wrapping up current work."
    )
    return state, response


def handle_pre_tool_use(
    state: SessionState,
    tool_name: str,
    file_path: str,
    command: str,
    agent: str = "",
) -> tuple:
    """Handle PreToolUse: path protection + edit recovery + session limits.

    `agent` is the host id (claude-code, cursor, gemini, ...) so host-specific
    rules such as the stamp_skill block apply only where they belong.
    """
    state.tool_calls += 1

    # Edit failure recovery: block everything except Read on the failed file
    if state.pending_failed_edit:
        failed_file = state.pending_failed_edit
        # Normalize both paths for comparison (resolve absolute vs relative)
        _norm_fp = str(Path(file_path).resolve()) if file_path else ""
        _norm_ff = str(Path(failed_file).resolve()) if failed_file else ""
        # Allow Read on the failed file (to recover)
        if tool_name == "Read" and (_norm_fp == _norm_ff):
            pass  # allow through
        # Allow Bash (need git, tests, etc.)
        elif tool_name == "Bash":
            pass  # allow through
        else:
            filename = Path(failed_file).name
            return state, (
                f"Edit to {filename} failed — re-read {failed_file} first, then retry."
            ), True

    # Retry loop detection — same error 3+ times means agent is stuck
    if state.recent_errors and len(state.recent_errors) >= RETRY_LOOP_THRESHOLD:
        last_errors = state.recent_errors[-RETRY_LOOP_THRESHOLD:]
        if len(set(last_errors)) == 1:
            return state, (
                f"RETRY LOOP DETECTED: Same error {RETRY_LOOP_THRESHOLD} times in a row. "
                f"Stop and try a DIFFERENT approach. Error: {last_errors[0][:80]}..."
            ), True

    # Damage radius check — too many files edited
    if tool_name in ("Edit", "Write") and file_path:
        n_files = len(state.files_edited)
        if n_files >= DAMAGE_RADIUS_BLOCK:
            return state, (
                f"DAMAGE RADIUS: {n_files} files edited this session (limit: {DAMAGE_RADIUS_BLOCK}). "
                f"This is likely off track. Confirm with the user before continuing."
            ), True
        if n_files == DAMAGE_RADIUS_WARN:
            # Warn once at threshold (not every subsequent edit)
            pass  # warning injected below, not blocking

    # Bash source-write detection — invalidate precommit if Bash modifies source files
    if tool_name == "Bash" and command:
        _invalidate_precommit_on_bash(command, Path.cwd())

    blocked, block_msg = check_protected_paths(
        state, tool_name, file_path, command, agent=agent
    )
    if blocked:
        return state, block_msg, True

    # Damage radius warning (non-blocking, injected as context)
    blast_warning = ""
    if tool_name in ("Edit", "Write") and len(state.files_edited) == DAMAGE_RADIUS_WARN:
        blast_warning = (
            f"DAMAGE RADIUS WARNING: {DAMAGE_RADIUS_WARN} unique files edited this session. "
            f"If this is a targeted change, you may be touching too many files. "
            f"Files so far: {', '.join(Path(f).name for f in state.files_edited[-5:])}"
        )

    state, response = apply_session_limits(state)
    if blast_warning and not response:
        response = blast_warning
    elif blast_warning and response:
        response = blast_warning + "\n\n" + response
    return state, response, False


# Per-host compaction event names (see scripts/config_generator.py COMPACTION_EVENT).
COMPACTION_EVENTS = {"PostCompact", "preCompact", "PreCompact", "post-compact"}


def parse_input(raw_input: str) -> dict:
    """Parse JSON input from the hook system. Non-object or malformed → {}."""
    from hook_io import read_hook_event

    return read_hook_event(raw_input)


def main() -> int:
    """Read event from stdin, dispatch to handler, output JSON response."""
    from hook_io import parse_hook_stdin, make_block_json, make_context_json

    raw_input = sys.stdin.read()
    event = parse_input(raw_input)

    if not event:
        return 0

    state_file = Path(SESSION_DIR) / STATE_FILENAME

    agent, canonical = parse_hook_stdin(raw_input)
    hook_event = canonical.get("event") or event.get("hook_event_name", "")
    tool_name = canonical.get("tool_name") or event.get("tool_name", "")
    tool_result = event.get("tool_result", "")

    file_path = canonical.get("file_path") or ""
    command = canonical.get("command") or ""

    state = load_state(state_file)

    response = ""
    blocked = False

    if hook_event == "UserPromptSubmit":
        state, response = handle_user_prompt(state)

    elif hook_event == "PostToolUse":
        result_text = tool_result if isinstance(tool_result, str) else json.dumps(tool_result)
        state, edit_response = handle_post_tool_use(
            state, result_text,
            tool_name=tool_name, command=command, file_path=file_path,
        )
        if edit_response:
            response = edit_response

    elif hook_event in COMPACTION_EVENTS or (
        hook_event == "SessionStart" and str(event.get("source", "")) == "compact"
    ):
        # Claude Code / Grok: SessionStart with source "compact".
        # Cursor: preCompact. Windsurf: post-compact. Legacy hosts: PostCompact.
        state, response = handle_post_compact(state)

    elif hook_event == "PreToolUse":
        state, response, blocked = handle_pre_tool_use(
            state, tool_name, file_path, command, agent=agent
        )

    elif "prompt" in event or canonical.get("prompt"):
        state, response = handle_user_prompt(state)

    elif tool_name:
        state, response, blocked = handle_pre_tool_use(
            state, tool_name, file_path, command, agent=agent
        )

    save_state(state, state_file)

    if response:
        event_name = hook_event or ("PreToolUse" if tool_name else "UserPromptSubmit")
        if blocked:
            print(make_block_json(response, agent=agent, event=event_name))
        else:
            print(make_context_json(response, agent=agent, event=event_name))

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
    "check_compact_threshold",
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
    from hook_io import run_guarded

    sys.exit(run_guarded(main, "session_monitor"))
