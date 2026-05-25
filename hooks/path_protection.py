"""G-SESSION-1, G-GATE-1, G-REPORT-1 path protection for session_monitor."""

import re

from session_state import SessionState

BASH_WRITE_PATTERNS = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir)"
)
BASH_REPORTS_WRITE = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir|cat\s*<<|printf)"
)

PROTECTED_PATHS = (
    {
        "marker": ".session/",
        "suffix": ".session",
        "path_key": ".session",
        "bash_ref": re.compile(r"\.session(/|\s|$)"),
        "rule": "G-SESSION-1",
        "message": (
            "BLOCKED: Agent must not modify .session/ files "
            "(G-SESSION-1). Session state is managed by hooks only."
        ),
    },
    {
        "marker": ".gates/",
        "suffix": ".gates",
        "path_key": ".gates",
        "bash_ref": re.compile(r"\.gates(/|\s|$)"),
        "rule": "G-GATE-1",
        "message": (
            "BLOCKED: Agent must not modify .gates/ files "
            "(G-GATE-1). Gate files are written by skill hooks only."
        ),
    },
    {
        "marker": "reports/",
        "suffix": "/reports",
        "path_key": "reports",
        "bash_ref": re.compile(r"\breports(/|\s|$)"),
        "rule": "G-REPORT-1",
        "message": (
            "BLOCKED: Agent must not write to reports/ "
            "(G-REPORT-1). Reports are produced by skill hooks only."
        ),
        "reports_bash": True,
    },
)


def _path_matches(file_path: str, marker: str, suffix: str) -> bool:
    if marker in file_path:
        return True
    if suffix.startswith("/"):
        return file_path.rstrip("/").endswith(suffix)
    return file_path.endswith(suffix)


def _bash_targets_path(command: str, bash_ref: re.Pattern, path_key: str) -> bool:
    if not bash_ref.search(command):
        return False
    if BASH_WRITE_PATTERNS.search(command):
        return True
    if ">" in command and path_key in command:
        return True
    if path_key == "reports" and (">>" in command):
        return True
    if path_key == "reports" and BASH_REPORTS_WRITE.search(command):
        return True
    return False


def _check_one_path(
    tool_name: str,
    file_path: str,
    command: str,
    marker: str,
    suffix: str,
    bash_ref: re.Pattern,
    path_key: str,
    message: str,
    reports_bash: bool = False,
) -> tuple:
    if tool_name in ("Write", "Edit"):
        if _path_matches(file_path, marker, suffix):
            return True, message
        return False, ""

    if tool_name == "Bash" and command:
        if reports_bash:
            if _bash_targets_path(command, bash_ref, path_key):
                return True, message
        elif bash_ref.search(command):
            if BASH_WRITE_PATTERNS.search(command) or (
                ">" in command and path_key in command
            ):
                return True, message
        return False, ""

    return False, ""


def check_protected_paths(
    state: SessionState,
    tool_name: str,
    file_path: str,
    command: str,
) -> tuple:
    """Run G-SESSION-1, G-GATE-1, G-REPORT-1 checks. Returns (blocked, message)."""
    for spec in PROTECTED_PATHS:
        if spec["rule"] == "G-GATE-1" and not state.gate_protect:
            continue
        if spec["rule"] == "G-REPORT-1" and not state.report_protect:
            continue

        path_key = spec["path_key"]
        blocked, msg = _check_one_path(
            tool_name,
            file_path,
            command,
            spec["marker"],
            spec["suffix"],
            spec["bash_ref"],
            path_key,
            spec["message"],
            reports_bash=spec.get("reports_bash", False),
        )
        if blocked:
            return True, msg

    return False, ""


# Backward-compatible names for tests that import directly
def check_session_blocked(tool_name: str, file_path: str, command: str) -> tuple:
    spec = PROTECTED_PATHS[0]
    return _check_one_path(
        tool_name, file_path, command,
        spec["marker"], spec["suffix"], spec["bash_ref"],
        ".session", spec["message"],
    )


def check_gates_blocked(tool_name: str, file_path: str, command: str) -> tuple:
    spec = PROTECTED_PATHS[1]
    return _check_one_path(
        tool_name, file_path, command,
        spec["marker"], spec["suffix"], spec["bash_ref"],
        ".gates", spec["message"],
    )


def check_reports_blocked(tool_name: str, file_path: str, command: str) -> tuple:
    spec = PROTECTED_PATHS[2]
    return _check_one_path(
        tool_name, file_path, command,
        spec["marker"], spec["suffix"], spec["bash_ref"],
        "reports", spec["message"], reports_bash=True,
    )
