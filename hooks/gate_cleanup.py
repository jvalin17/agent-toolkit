#!/usr/bin/env python3
"""gate_cleanup.py — Selective gate flag cleanup after git commit/push.

Commit consumes commit-scoped gates (precommit). Push-scoped gates
(evaluate, reviewer, assess) survive commit so you can finalize once
then commit → push without re-running every skill.

Runs as PostToolUse hook on Bash tool.

Replaces gate-cleanup.sh.
"""

import json
import re
import sys
from pathlib import Path
from typing import Tuple

COMMIT_GATE_FLAGS = frozenset({"precommit-passed"})
PUSH_GATE_FLAGS = frozenset(
    {"evaluate-passed", "reviewer-passed", "assess-passed"}
)


def _strip_quoted(command: str) -> str:
    stripped = re.sub(r"'[^']*'", "", command)
    return re.sub(r'"[^"]*"', "", stripped)


def _command_segments(command: str) -> list[str]:
    return [
        seg.strip()
        for seg in re.split(r"&&|;|\|", _strip_quoted(command))
        if seg.strip()
    ]


def is_git_commit(command: str) -> bool:
    """Check if a command contains git commit (not inside quotes)."""
    for segment in _command_segments(command):
        if re.search(r"^git\s+commit", segment):
            return True
    return False


def is_git_push(command: str) -> bool:
    """Check if a command contains git push (not inside quotes)."""
    for segment in _command_segments(command):
        if re.search(r"^git\s+.*\s+push|^git\s+push", segment):
            return True
    return False


def _remove_gate_flags(gates_dir: Path, flag_names: frozenset[str]) -> None:
    if not gates_dir.is_dir():
        return
    for name in flag_names:
        flag = gates_dir / name
        if flag.is_file():
            flag.unlink()


def _clear_signed_gate_files(project_dir: Path) -> None:
    gate_dir = project_dir / ".gate"
    for filename in ("gate-token.jwt", "attestation.json"):
        token_file = gate_dir / filename
        if token_file.is_file():
            token_file.unlink()


def run_gate_cleanup(
    stdin_input: str,
    project_dir: Path,
) -> Tuple[int, str]:
    """Main cleanup logic. Returns (exit_code, output)."""
    try:
        hook_input = json.loads(stdin_input)
        command = hook_input.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0, ""

    if not command:
        return 0, ""

    has_commit = is_git_commit(command)
    has_push = is_git_push(command)
    if not has_commit and not has_push:
        return 0, ""

    gates_dir = project_dir / ".gates"

    if has_commit:
        _remove_gate_flags(gates_dir, COMMIT_GATE_FLAGS)
        _clear_signed_gate_files(project_dir)

    if has_push:
        _remove_gate_flags(gates_dir, PUSH_GATE_FLAGS)
        _clear_signed_gate_files(project_dir)

    return 0, ""


def main() -> int:
    """Entry point — reads hook input from stdin."""
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()
    exit_code, output = run_gate_cleanup(stdin_input, project_dir)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
