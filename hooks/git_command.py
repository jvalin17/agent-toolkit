"""Find git commit / push anywhere inside a shell command line.

Security property: fail closed. Wrappers (`bash -c`, `eval`, `env`, `FOO=1`),
absolute paths, newlines, `;`, `&&`, `||`, `|`, `&`, subshells, braces and
command substitutions must all be seen through. False positives only cost a
"run /precommit first" message; false negatives bypass the gate.
"""

from __future__ import annotations

import re
import shlex
from typing import Iterable, Set

GATED_SUBCOMMANDS = {"commit", "push"}

# Tokens that run the *next* token as a command.
EXEC_WRAPPERS = {"env", "command", "exec", "nohup", "xargs", "sudo", "doas", "time", "nice", "ionice"}
# Shells whose -c argument is itself a command line.
SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish"}
# git global options that take a value before the subcommand.
GIT_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix"}
# Subcommand options that mean "do nothing": these are not gated.
DRY_RUN_FLAGS = {"--dry-run", "-n", "--help", "-h"}

_SEPARATORS = re.compile(r"\n|;|&&|\|\||\||&")
_SUBSTITUTION = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_LOOSE_GIT = re.compile(r"\bgit\b[^\n;|&]*?\b(commit|push)\b")


def _segments(command: str) -> Iterable[str]:
    for seg in _SEPARATORS.split(command):
        seg = seg.strip().strip("(){}").strip()
        if seg:
            yield seg


def _tokens(segment: str) -> list[str] | None:
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return None


def _git_action(tokens: list[str], start: int) -> str | None:
    """Return 'commit' / 'push' if tokens[start] is git followed by a gated subcommand."""
    i = start + 1
    while i < len(tokens):
        tok = tokens[i]
        if tok in GIT_VALUE_OPTIONS:
            i += 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        if tok in GATED_SUBCOMMANDS:
            rest = tokens[i + 1:]
            if any(r in DRY_RUN_FLAGS for r in rest):
                return None
            return tok
        return None
    return None


def _scan_tokens(tokens: list[str], found: Set[str]) -> None:
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        base = tok.rsplit("/", 1)[-1]
        if _ENV_ASSIGNMENT.match(tok) or base in EXEC_WRAPPERS or tok.startswith("-"):
            i += 1
            continue
        if base == "git":
            action = _git_action(tokens, i)
            if action:
                found.add(action)
            return
        if base in SHELLS or base == "eval":
            # Everything after the shell/eval is a nested command line.
            for inner in tokens[i + 1:]:
                if not inner.startswith("-"):
                    found.update(detect_git_actions(inner))
            return
        # Any other command: still recurse into string arguments that look like
        # command lines (e.g. xargs/sudo/env handled above; python -c is not).
        i += 1


def detect_git_actions(command: str) -> Set[str]:
    """Set of gated git actions ('commit', 'push') present anywhere in `command`."""
    found: Set[str] = set()
    if not command or not command.strip():
        return found

    # Command substitutions run too — scan their bodies first.
    for match in _SUBSTITUTION.finditer(command):
        found.update(detect_git_actions(match.group(1) or match.group(2) or ""))

    for segment in _segments(command):
        tokens = _tokens(segment)
        if tokens is None:
            # Unparseable (unbalanced quotes): fail closed on a loose match.
            for m in _LOOSE_GIT.finditer(segment):
                found.add(m.group(1))
            continue
        _scan_tokens(tokens, found)
    return found


def detect_git_action(command: str) -> str | None:
    """Single highest-priority action for callers that want one: push > commit > None."""
    actions = detect_git_actions(command)
    if "push" in actions:
        return "push"
    if "commit" in actions:
        return "commit"
    return None
