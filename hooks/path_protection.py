"""G-SESSION-1, G-GATE-1, G-REPORT-1 path protection for session_monitor."""

import re

from session_state import SessionState

BASH_WRITE_PATTERNS = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir)"
    r".*\.session"
)
BASH_SESSION_REF = re.compile(r"\.session(/|\s|$)")

BASH_GATES_WRITE = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir)"
    r".*\.gates"
)
BASH_GATES_REF = re.compile(r"\.gates(/|\s|$)")

BASH_REPORTS_WRITE = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir|cat\s*<<|printf)"
    r".*\breports(/|\b)"
)
BASH_REPORTS_REF = re.compile(r"\breports(/|\s|$)")


def check_session_blocked(
    tool_name: str, file_path: str, command: str
) -> tuple:
    """G-SESSION-1: Block agent writes to .session/. Returns (blocked, message)."""
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
    """G-GATE-1: Block agent writes to .gates/. Returns (blocked, message)."""
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
    """G-REPORT-1: Block agent writes to reports/. Returns (blocked, message)."""
    msg = (
        "BLOCKED: Agent must not write to reports/ "
        "(G-REPORT-1). Reports are produced by skill hooks only."
    )

    if tool_name in ("Write", "Edit"):
        if "reports/" in file_path or file_path.rstrip("/").endswith("/reports"):
            return True, msg
        return False, ""

    if tool_name == "Bash" and command:
        if BASH_REPORTS_REF.search(command):
            if BASH_REPORTS_WRITE.search(command):
                return True, msg
            if (">" in command or ">>" in command) and "reports" in command:
                return True, msg
        return False, ""

    return False, ""


def check_protected_paths(
    state: SessionState,
    tool_name: str,
    file_path: str,
    command: str,
) -> tuple:
    """Run G-SESSION-1, G-GATE-1, G-REPORT-1 checks. Returns (blocked, message)."""
    blocked, block_msg = check_session_blocked(tool_name, file_path, command)
    if blocked:
        return True, block_msg

    if state.gate_protect:
        blocked, block_msg = check_gates_blocked(tool_name, file_path, command)
        if blocked:
            return True, block_msg

    if state.report_protect:
        blocked, block_msg = check_reports_blocked(tool_name, file_path, command)
        if blocked:
            return True, block_msg

    return False, ""
