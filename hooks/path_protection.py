"""Path protection for session_monitor — G-SESSION-1, G-GATE-1, G-REPORT-1, G-CONFIG-1.

Model: **default deny**. A Bash command that names a protected path is allowed
only when every segment of it is a known read-only command with no write
redirect. Anything else (touch, python -c, ln, cp, tee, dd, a redirect) is
blocked. Edit/Write to protected paths is blocked outright. The Read tool is
blocked on secret files (signing and flag keys) and on .session/.

This is text matching; an agent can evade it by building paths at runtime.
It stops drift and casual forgery. The backstop against a hostile agent is
signed mode with the secret held in CI (see gate/flags.py docstring).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from git_command import _segments, _tokens  # noqa: E402
from session_state import SessionState  # noqa: E402

# --- Protected locations --------------------------------------------------------

# Hook-managed directories: readable, never writable by the agent.
PROTECTED_PATHS = (
    {
        "marker": ".session/",
        "suffix": ".session",
        "path_key": ".session",
        "bash_ref": re.compile(r"\.session(/|\s|$|['\"])"),
        "rule": "G-SESSION-1",
        "read_tool": "deny",
        "message": ".session/ is hook-managed — use a different path.",
    },
    {
        "marker": ".gates/",
        "suffix": ".gates",
        "path_key": ".gates",
        "bash_ref": re.compile(r"\.gates(/|\s|$|['\"])"),
        "rule": "G-GATE-1",
        "read_tool": "allow",
        "message": ".gates/ is hook-managed — run /precommit or /evaluate instead.",
    },
    {
        "marker": "reports/",
        "suffix": "/reports",
        "path_key": "reports",
        "bash_ref": re.compile(r"\breports(/|\s|$|['\"])"),
        "rule": "G-REPORT-1",
        "read_tool": "allow",
        "message": "reports/ is hook-managed — use finalize_report.py to write reports.",
    },
    {
        "marker": ".gate/",
        "suffix": ".gate",
        "path_key": ".gate",
        "bash_ref": re.compile(r"\.gate(/|\s|$|['\"])"),
        "rule": "G-GATE-1",
        "read_tool": "allow",
        "message": ".gate/ holds the signing key and token — hook-managed, use setup-signed-gates.sh.",
    },
)

# Policy files: the agent may read them, never write them (G-CONFIG-1).
CONFIG_FILE_PATTERNS = (
    re.compile(r"(^|/)gates\.json$"),
    re.compile(r"(^|/)\.claude/settings(\.local)?\.json$"),
    re.compile(r"(^|/)\.(cursor|grok|windsurf)/hooks\.json$"),
    re.compile(r"(^|/)\.codex/config\.toml$"),
    re.compile(r"(^|/)\.agent-toolkit/"),
)
# Toolkit sources that merely look like policy files (templates, reference copies).
CONFIG_FILE_EXEMPT = re.compile(r"(^|/)(templates|hooks)/(gates|hooks)\.json$")
CONFIG_BASH_REF = re.compile(
    r"(^|[\s/'\"])(gates\.json|\.claude/settings(\.local)?\.json|\.(cursor|grok|windsurf)/hooks\.json|\.codex/config\.toml|\.agent-toolkit/)"
)
CONFIG_MESSAGE = (
    "G-CONFIG-1: {name} is enforcement policy and is hook-managed — the agent may read it, "
    "not change it. Ask the user to edit it, or use /agent-toolkit-mode for the mode."
)

# Secret material: never readable by the agent through any tool.
SECRET_FILE_PATTERNS = (
    re.compile(r"(^|/)signing\.key$"),
    re.compile(r"(^|/)private\.pem$"),
    re.compile(r"(^|/)flag\.key$"),
    re.compile(r"(^|/)gate-token\.jwt$"),
)
SECRET_BASH_REF = re.compile(r"signing\.key|private\.pem|flag\.key|gate-token\.jwt")
SECRET_MESSAGE = (
    "G-GATE-1: {name} is secret gate material — the agent may not read, copy or write it."
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

# --- Read-only command allowlist ---------------------------------------------------

READ_ONLY_COMMANDS = {
    "cat", "ls", "head", "tail", "less", "more", "grep", "egrep", "fgrep", "rg", "ag",
    "stat", "file", "wc", "find", "diff", "cmp", "md5sum", "shasum", "sha256sum",
    "test", "[", "[[", "true", "jq", "awk", "cut", "sort", "uniq", "tr", "column",
    "printf", "echo", "pwd", "realpath", "readlink", "basename", "dirname", "du", "tree",
    "git",
}
# git subcommands that rewrite working-tree files. Everything else (status,
# diff, log, add, commit, push, ...) reads files or only touches .git/.
GIT_WRITE_SUBCOMMANDS = {
    "checkout", "restore", "switch", "rm", "mv", "clean", "reset", "revert", "merge",
    "rebase", "cherry-pick", "apply", "pull", "stash", "am", "worktree", "sparse-checkout",
}
# `cmd > file` or `cmd >> file` writes; `2>/dev/null` and `>/dev/null` do not.
WRITE_REDIRECT = re.compile(r"(?<![0-9])>{1,2}\s*(?!/dev/null)|[0-9]>{1,2}\s*(?!&?[0-9]|/dev/null)")
ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Programs that execute a heredoc body as code; for anything else the body is data.
INTERPRETERS = {"bash", "sh", "zsh", "dash", "ksh", "python", "python3", "node", "perl", "ruby", "php"}
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\s*\2(?=\n|$)", re.DOTALL)


def _strip_data_heredocs(command: str) -> str:
    """Drop heredoc bodies that are data (commit messages, file contents).

    A body fed to an interpreter (`bash <<EOF`, `python3 - <<EOF`) stays, because
    those lines run as commands.
    """
    def replace(match: re.Match) -> str:
        line_start = command.rfind("\n", 0, match.start()) + 1
        opener_line = command[line_start:match.start()]
        # Only the command the heredoc is attached to matters, not earlier
        # `&&`/`;` segments on the same line.
        opener = list(_segments(opener_line))[-1] if opener_line.strip() else ""
        tokens = _tokens(opener) or opener.split()
        names = {t.rsplit("/", 1)[-1] for t in tokens}
        if names & INTERPRETERS:
            return match.group(0)
        return match.group(0)[: match.start(3) - match.start()] + "<heredoc-data>" + match.group(0)[match.end(3) - match.start():]

    return HEREDOC.sub(replace, command)


def _segment_is_read_only(segment: str) -> bool:
    if WRITE_REDIRECT.search(segment):
        return False
    tokens = _tokens(segment)
    if tokens is None:
        return False  # unparseable → fail closed
    tokens = [t for t in tokens if not ENV_ASSIGNMENT.match(t)]
    if not tokens:
        return True
    cmd = tokens[0].rsplit("/", 1)[-1]
    if cmd not in READ_ONLY_COMMANDS:
        return False
    if cmd == "git":
        sub = next((t for t in tokens[1:] if not t.startswith("-")), "")
        return sub not in GIT_WRITE_SUBCOMMANDS
    if cmd in ("awk", "sed") and any(t in ("-i", "--in-place") for t in tokens):
        return False
    return True


def _command_is_read_only(command: str) -> bool:
    """Every segment must be a read-only command; one writer poisons the whole line."""
    return all(_segment_is_read_only(seg) for seg in _segments(command))


# --- Checks ---------------------------------------------------------------------------


def _path_matches(file_path: str, marker: str, suffix: str) -> bool:
    if marker in file_path:
        return True
    if suffix.startswith("/"):
        return file_path.rstrip("/").endswith(suffix)
    return file_path.endswith(suffix)


def _is_config_file(file_path: str) -> bool:
    if CONFIG_FILE_EXEMPT.search(file_path):
        return False
    return any(p.search(file_path) for p in CONFIG_FILE_PATTERNS)


def _is_secret_file(file_path: str) -> bool:
    return any(p.search(file_path) for p in SECRET_FILE_PATTERNS)


def _is_gate_writing_tool(tool_name: str) -> bool:
    return tool_name in GATE_WRITING_TOOLS or tool_name.endswith("__stamp_skill")


def _host_stamps_via_hook(agent: str) -> bool:
    """True when the host writes stamps from its Skill hook (so CLI stamps are forgeries)."""
    from host_config import load_host_config, resolve_host

    cfg = load_host_config(agent) if agent else resolve_host()
    return cfg.get("stamp_mode") == HOOK_STAMP_MODE


def _check_edit_tool(file_path: str, state: SessionState) -> Optional[str]:
    if _is_secret_file(file_path):
        return SECRET_MESSAGE.format(name=file_path.rsplit("/", 1)[-1])
    for spec in PROTECTED_PATHS:
        if not _rule_enabled(spec["rule"], state):
            continue
        if _path_matches(file_path, spec["marker"], spec["suffix"]):
            return spec["message"]
    if state.gate_protect and _is_config_file(file_path):
        return CONFIG_MESSAGE.format(name=file_path.rsplit("/", 1)[-1] or file_path)
    return None


def _check_read_tool(file_path: str, state: SessionState) -> Optional[str]:
    if _is_secret_file(file_path):
        return SECRET_MESSAGE.format(name=file_path.rsplit("/", 1)[-1])
    for spec in PROTECTED_PATHS:
        if spec["read_tool"] == "deny" and _rule_enabled(spec["rule"], state):
            if _path_matches(file_path, spec["marker"], spec["suffix"]):
                return spec["message"]
    return None


def _check_bash(command: str, state: SessionState) -> Optional[str]:
    command = _strip_data_heredocs(command)
    if SECRET_BASH_REF.search(command):
        return SECRET_MESSAGE.format(name="the gate key material")
    read_only = _command_is_read_only(command)
    for spec in PROTECTED_PATHS:
        if not _rule_enabled(spec["rule"], state):
            continue
        if spec["bash_ref"].search(command) and not read_only:
            return spec["message"] + " (only read-only commands may name this path)"
    if state.gate_protect and CONFIG_BASH_REF.search(command) and not read_only:
        return CONFIG_MESSAGE.format(name="that policy file")
    return None


def _rule_enabled(rule: str, state: SessionState) -> bool:
    if rule == "G-GATE-1":
        return state.gate_protect
    if rule == "G-REPORT-1":
        return state.report_protect
    return True


def check_protected_paths(
    state: SessionState,
    tool_name: str,
    file_path: str,
    command: str,
    agent: str = "",
) -> tuple:
    """Run the path rules. Returns (blocked, message).

    `agent` is the host id from the hook payload (hook_io.parse_hook_stdin);
    empty means detect from the environment.
    """
    if state.gate_protect and _is_gate_writing_tool(tool_name) and _host_stamps_via_hook(agent):
        return True, GATE_WRITING_TOOL_MESSAGE

    message: Optional[str] = None
    if tool_name in ("Write", "Edit", "MultiEdit", "NotebookEdit") and file_path:
        message = _check_edit_tool(file_path, state)
    elif tool_name == "Read" and file_path:
        message = _check_read_tool(file_path, state)
    elif tool_name == "Bash" and command:
        message = _check_bash(command, state)

    return (True, message) if message else (False, "")


# Backward-compatible names for tests that import directly
def _single_rule(index: int, tool_name: str, file_path: str, command: str) -> tuple:
    spec = PROTECTED_PATHS[index]
    if tool_name in ("Write", "Edit"):
        return (True, spec["message"]) if _path_matches(file_path, spec["marker"], spec["suffix"]) else (False, "")
    if tool_name == "Bash" and command:
        if spec["bash_ref"].search(command) and not _command_is_read_only(command):
            return True, spec["message"]
    return False, ""


def check_session_blocked(tool_name: str, file_path: str, command: str) -> tuple:
    return _single_rule(0, tool_name, file_path, command)


def check_gates_blocked(tool_name: str, file_path: str, command: str) -> tuple:
    return _single_rule(1, tool_name, file_path, command)


def check_reports_blocked(tool_name: str, file_path: str, command: str) -> tuple:
    return _single_rule(2, tool_name, file_path, command)
