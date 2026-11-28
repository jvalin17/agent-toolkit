"""Path protection for session_monitor — G-SESSION-1, G-GATE-1, G-REPORT-1, G-CONFIG-1.

Model: **default deny**. A Bash command that names a protected path is allowed
only when every segment of it is a known read-only command with no write
redirect. Anything else (touch, python -c, ln, cp, tee, dd, a redirect) is
blocked. Edit/Write to protected paths is blocked outright. The Read tool is
blocked on secret files (signing and flag keys) and on .session/.

This is text matching; an agent can evade it by building paths at runtime.
For ~/.agent-toolkit a write is also refused when the command shows a name
that could become the folder's (a glob, a spliced variable, a string cut off
mid-name); a command that shows none is still not seen. It stops drift and casual forgery. The backstop against a hostile agent is
signed mode with the secret held in CI (see gate/flags.py docstring).
"""

from __future__ import annotations

import re
import sys
from fnmatch import fnmatchcase
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
    re.compile(r"(^|/)\.agent-toolkit(/|$)"),
)
# Toolkit sources that merely look like policy files (templates, reference copies).
CONFIG_FILE_EXEMPT = re.compile(r"(^|/)(templates|hooks)/(gates|hooks)\.json$")
CONFIG_BASH_REF = re.compile(
    r"(^|[\s/'\"])(gates\.json|\.claude/settings(\.local)?\.json|\.(cursor|grok|windsurf)/hooks\.json|\.codex/config\.toml|\.agent-toolkit(?![\w.-]))"
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


# --- The toolkit's home folder under another spelling ---------------------------------------
#
# ~/.agent-toolkit holds the signing key and the developer-mode record. A write
# is refused when the command shows a name the shell, or code joining strings,
# could turn into that folder. Nothing is run or expanded: text decided at run
# time counts as "anything", and the question is only whether the name fits.
#
#   1. a name starting ".agen" that could end up as the folder's name;
#   2. a name directly under the home folder that could: a dotted one, one
#      the shell fills in at run time, or the pattern of a `find` that acts;
#      and, wherever it points, an unquoted dotted glob with a letter in it
#      that fits (`cd ~ && rm -rf .a*`);
#   3. the record's file name, "dev-repo", inside a folder that is hidden,
#      globbed or pieced together, or as the bare target of a redirect.
#
# A command that shows none of these (the name joined from pieces that do not
# start with ".agen", or changed after it is written out; the record named by a
# glob after a `cd` into the folder; a script kept in a file) is not seen. No
# reading of the command text can see it.

TOOLKIT_HOME = ".agent-toolkit"
RECORD_NAME = "dev-repo"
MAX_NAME_LENGTH = 128  # a longer name is refused unread: no real name here is that long
# A name runs to the next space or slash; a slash inside ${...} is part of the name.
NAME_REST = r"(?:\$\{[^}\s]{0,64}\}|[^\s/])*"
TOOLKIT_HOME_START = re.compile(r"(?<![\w.])(\.agen" + NAME_REST + ")")
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")  # the shell expands no glob in there
DOTTED_GLOB = re.compile(r"(?<![\w.])(\.[\w.\-*?\[\]!^]+)")
LETTER_OUTSIDE_BRACKETS = re.compile(r"[a-z]")
GLOB_CHARACTERS = "*?["
NAME_UNDER_HOME = re.compile(
    r"(?:~|\$home|\$\{home\}|/users/[^/\s'\"]+|/home/[^/\s'\"]+|/root)['\"]?/+(?:\./+)*['\"]?(" + NAME_REST + ")"
)
ONE_PLAIN_VARIABLE = re.compile(r"(?:\$\w+|\$\{\w+\})\Z")
FIND_NAME_TEST = re.compile(r"-i?(?:name|path|wholename)\s+['\"]?([^\s'\"]+)")
RECORD_IN_FOLDER = re.compile(r"/" + RECORD_NAME + r"(?![\w.-])")
FOLDER_START = re.compile(r"[\s/]")
RECORD_AS_REDIRECT_TARGET = re.compile(r">\s*['\"]?" + RECORD_NAME + r"(?![\w.-])")
RUN_TIME_TEXT = re.compile(r"\$\{[^{}]*\}?|\$\(.*|`.*|\$\w+|\$.?")
NAME_END = re.compile(r"[;|&()<>:]")
ASSEMBLED = re.compile(r"[^\w.\-*?\[\]!^{},]")  # a quote, a backslash, %s, @: more text follows from elsewhere
BRACE_LIST = re.compile(r"\{([^{}]*)\}")
LIST_END = re.compile(r"[{},]")
BRACKET_GLOB = re.compile(r"\[[^\]]*\]\]?")  # any one character: more than the glob allows, never less
PLAIN_FOLDER = re.compile(r"(?:~|\$\w+|\$\{\w+\}|[a-z0-9_-][\w.-]*)\Z")
QUOTES = re.compile(r"['\"]")
FIND_ACTIONS = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint", "-fprint0", "-fprintf", "-fls"}
RUNS_ANOTHER_COMMAND = re.compile(r"\$\(|`|[<>]\(|\bsystem\s*\(")


DISGUISE_MESSAGE = (
    "G-CONFIG-1: this command could write to ~/.agent-toolkit: a glob, a variable or a name put together "
    "in it fits that folder, which holds the signing key and is hook-managed. If you mean another path, "
    "write that path out in full. Ask the user to make any change inside ~/.agent-toolkit."
)


def _reads_only_in_name(command: str) -> bool:
    """True when a command on the read-only list is told to delete, write or run something."""
    if RUNS_ANOTHER_COMMAND.search(command):
        return True
    for segment in _segments(command):
        tokens = _tokens(segment) or segment.split()
        names = {t.rsplit("/", 1)[-1] for t in tokens}
        if "find" in names and FIND_ACTIONS & set(tokens):
            return True
        if "sort" in names and any(t == "-o" or t.startswith("--output") for t in tokens):
            return True
        if "git" in names and "config" in tokens:
            return True
    return False


def _can_become_toolkit_home(name: str) -> bool:
    """Could the shell, or code joining strings, turn ``name`` into `.agent-toolkit`?"""
    if len(name) > MAX_NAME_LENGTH:
        return True
    name = BRACKET_GLOB.sub("?", RUN_TIME_TEXT.sub("*", name))
    name = NAME_END.split(name, maxsplit=1)[0]
    assembled = ASSEMBLED.search(name)
    if assembled:
        name = name[:assembled.start()] + "*"
    if name in (".agen", ".agent-"):
        return True  # nothing is called that: the rest comes from somewhere else
    spellings = [name]
    for _ in range(2):  # brace lists, one inside another at most; anything deeper is left as written
        expanded = []
        for spelling in spellings:
            brace = BRACE_LIST.search(spelling)
            choices = brace.group(1).split(",") if brace else [None]
            if brace and len(choices) == 1:
                choices = ["*"]  # {name} and {} are filled in by code, not by the shell
            expanded += [spelling if c is None else spelling[:brace.start()] + c + spelling[brace.end():] for c in choices]
        spellings = expanded
    # A comma or brace left over belongs to a list that started before this name: the name ends there.
    return any(fnmatchcase(TOOLKIT_HOME, LIST_END.split(spelling, maxsplit=1)[0]) for spelling in spellings)


def _name_under_home_can_become_toolkit_home(name: str, any_glob_matches_dots: bool) -> bool:
    if name.startswith(".") or any_glob_matches_dots:
        return _can_become_toolkit_home(name)
    # `~/$PROJECT` is someone's folder; `~/${v%x}` and `~/$a$b` are put together on the spot.
    filled_in = "$" in name or "`" in name
    return filled_in and not ONE_PLAIN_VARIABLE.match(name) and _can_become_toolkit_home(name)


def _dotted_glob_fits_toolkit_home(word: str) -> bool:
    """`.a*` and `.[a]gent?toolkit` name the folder wherever they are used; `.*` and `.??*` name every dotted file."""
    if not any(c in word for c in GLOB_CHARACTERS) or len(word) > MAX_NAME_LENGTH:
        return False
    return LETTER_OUTSIDE_BRACKETS.search(BRACKET_GLOB.sub("", word)) is not None and _can_become_toolkit_home(word)


def _find_pattern_fits_toolkit_home(pattern: str) -> bool:
    """A `find` looks inside dotted names too, so its pattern needs no leading dot to fit."""
    last = pattern.rsplit("/", 1)[-1][:MAX_NAME_LENGTH]
    return last != "*" and fnmatchcase(TOOLKIT_HOME, BRACKET_GLOB.sub("?", last))


def _record_folder_is_suspect(text: str, end: int) -> bool:
    """The folder named just before ``end``: `src/dev-repo` is someone's folder; `.x/dev-repo`,
    `?gent*/dev-repo` and `$a$b/dev-repo` are not."""
    before = text[max(0, end - MAX_NAME_LENGTH - 1):end]
    last = QUOTES.sub("", FOLDER_START.split(before)[-1])
    return len(last) > MAX_NAME_LENGTH or PLAIN_FOLDER.match(last) is None


def _names_toolkit_home_in_disguise(command: str) -> bool:
    """True when the command names ~/.agent-toolkit, or its record, without spelling the folder out."""
    text = command.lower()
    if any(_can_become_toolkit_home(name) for name in TOOLKIT_HOME_START.findall(text)):
        return True
    dotglob = "dotglob" in text
    if any(_name_under_home_can_become_toolkit_home(name, dotglob) for name in NAME_UNDER_HOME.findall(text)):
        return True
    if any(_find_pattern_fits_toolkit_home(pattern) for pattern in FIND_NAME_TEST.findall(text)):
        return True
    if any(_dotted_glob_fits_toolkit_home(word) for word in DOTTED_GLOB.findall(QUOTED.sub(" ", text))):
        return True
    if any(_record_folder_is_suspect(text, found.start()) for found in RECORD_IN_FOLDER.finditer(text)):
        return True
    return RECORD_AS_REDIRECT_TARGET.search(text) is not None


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
    acts = not read_only or _reads_only_in_name(command)
    if state.gate_protect and acts and _names_toolkit_home_in_disguise(command):
        return DISGUISE_MESSAGE
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
