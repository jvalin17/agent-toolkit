"""G-SESSION-1, G-GATE-1, G-REPORT-1 path protection for session_monitor."""

import re

from session_state import SessionState

BASH_WRITE_PATTERNS = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir)"
)
BASH_REPORTS_WRITE = re.compile(
    r"(rm|mv|cp|echo|tee|sed\s+-i|chmod|chown|mkdir|cat\s*<<|printf)"
)

# MCP tools that write under .gates/. On hosts whose Skill hook writes stamps
# (hosts/<id>.json "stamp_mode": "hook_skill_passed" — Claude Code), an agent
# calling these is forging a stamp (G-GATE-1). On "cli_stamp" hosts (Cursor,
# Gemini, Codex, Grok, Windsurf) this tool is the legitimate stamping path.
GATE_WRITING_TOOLS = (
    "mcp__agent-toolkit__stamp_skill",
    "mcp__agent_toolkit__stamp_skill",
)
GATE_WRITING_TOOL_MESSAGE = (
    "G-GATE-1: stamp_skill writes to .gates/ and is not allowed from this host — "
    "stamps are written by the Skill hook. Run the skill via the Skill tool instead."
)
HOOK_STAMP_MODE = "hook_skill_passed"


def _is_gate_writing_tool(tool_name: str) -> bool:
    return tool_name in GATE_WRITING_TOOLS or tool_name.endswith("__stamp_skill")


def _host_stamps_via_hook(agent: str) -> bool:
    """True when the host writes stamps from its Skill hook (so CLI stamps are forgeries)."""
    from host_config import load_host_config, resolve_host

    cfg = load_host_config(agent) if agent else resolve_host()
    return cfg.get("stamp_mode") == HOOK_STAMP_MODE

PROTECTED_PATHS = (
    {
        "marker": ".session/",
        "suffix": ".session",
        "path_key": ".session",
        "bash_ref": re.compile(r"\.session(/|\s|$)"),
        "rule": "G-SESSION-1",
        "message": (
            ".session/ is hook-managed — use a different path."
        ),
    },
    {
        "marker": ".gates/",
        "suffix": ".gates",
        "path_key": ".gates",
        "bash_ref": re.compile(r"\.gates(/|\s|$)"),
        "rule": "G-GATE-1",
        "message": (
            ".gates/ is hook-managed — run /precommit or /evaluate instead."
        ),
    },
    {
        "marker": "reports/",
        "suffix": "/reports",
        "path_key": "reports",
        "bash_ref": re.compile(r"\breports(/|\s|$)"),
        "rule": "G-REPORT-1",
        "message": (
            "reports/ is hook-managed — use finalize_report.py to write reports."
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
    agent: str = "",
) -> tuple:
    """Run G-SESSION-1, G-GATE-1, G-REPORT-1 checks. Returns (blocked, message).

    `agent` is the host id from the hook payload (hook_io.parse_hook_stdin);
    empty means detect from the environment.
    """
    if (
        state.gate_protect
        and _is_gate_writing_tool(tool_name)
        and _host_stamps_via_hook(agent)
    ):
        return True, GATE_WRITING_TOOL_MESSAGE

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
