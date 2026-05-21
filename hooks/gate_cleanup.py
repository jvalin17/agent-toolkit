#!/usr/bin/env python3
"""gate_cleanup.py — Clears all gate flags after successful git commit.

Every new commit requires fresh skill passes.
Runs as PostToolUse hook on Bash tool.

Replaces gate-cleanup.sh.
"""

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Tuple


def is_git_commit(command: str) -> bool:
    """Check if a command is a git commit (not inside quotes)."""
    # Strip quoted strings to avoid matching commit messages
    stripped = re.sub(r"'[^']*'", "", command)
    stripped = re.sub(r'"[^"]*"', "", stripped)

    segments = re.split(r"&&|;|\|", stripped)
    for segment in segments:
        segment = segment.strip()
        if re.search(r"^git\s+commit", segment):
            return True
    return False


def run_gate_cleanup(
    stdin_input: str,
    project_dir: Path,
) -> Tuple[int, str]:
    """Main cleanup logic. Returns (exit_code, output).

    On git commit: removes .gates/ directory and signed gate files.
    On anything else: no-op.
    """
    try:
        hook_input = json.loads(stdin_input)
        command = hook_input.get("tool_input", {}).get("command", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0, ""

    if not command or not is_git_commit(command):
        return 0, ""

    # Remove legacy gate flags
    gates_dir = project_dir / ".gates"
    if gates_dir.is_dir():
        shutil.rmtree(gates_dir)

    # Remove signed gate files (but keep .gate/ dir if it has other files)
    gate_dir = project_dir / ".gate"
    for filename in ("gate-token.jwt", "attestation.json"):
        token_file = gate_dir / filename
        if token_file.is_file():
            token_file.unlink()

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
