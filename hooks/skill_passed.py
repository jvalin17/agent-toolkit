#!/usr/bin/env python3
"""skill_passed.py — Informs Claude about gate status after a gated skill runs.

This hook does NOT set gate flags. Only `hooks/finalize_report.py` writes
`.gates/*-passed` when `gate_protect` is on (precommit, evaluate, reviewer,
assess). This hook only tells Claude what gates are still needed.

Runs as PostToolUse hook on Skill tool.
Replaces skill-passed.sh.
"""

import json
import sys
from pathlib import Path
from typing import Tuple

GATED_SKILLS = ("precommit", "evaluate", "reviewer", "assess")


def make_hook_response(message: str) -> str:
    """Build Claude Code PostToolUse hook JSON response."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": message,
            }
        }
    )


def run_skill_passed(
    stdin_input: str,
    project_dir: Path,
) -> Tuple[int, str]:
    """Check gate status after a skill runs. Returns (exit_code, output)."""
    try:
        hook_input = json.loads(stdin_input)
        skill = hook_input.get("tool_input", {}).get("skill", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0, ""

    if not skill or skill not in GATED_SKILLS:
        return 0, ""

    gates_dir = project_dir / ".gates"
    flag_file = gates_dir / f"{skill}-passed"

    if flag_file.is_file():
        # Skill set its own flag — it passed. Report remaining gates.
        missing = [
            f"/{gated}"
            for gated in GATED_SKILLS
            if not (gates_dir / f"{gated}-passed").is_file()
        ]

        if missing:
            message = f"/{skill} PASSED — gate unlocked. Still needed: {' '.join(missing)}"
        else:
            message = f"/{skill} PASSED — all gates unlocked. git commit/push is allowed."
    else:
        # Skill did NOT set its flag — it did not pass
        message = (
            f"/{skill} ran but did NOT pass. Gate remains locked. "
            "The skill must end with a passing result to unlock the gate. "
            "Check the skill output for BLOCKED reasons."
        )

    return 0, make_hook_response(message)


def main() -> int:
    """Entry point — reads hook input from stdin."""
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()
    exit_code, output = run_skill_passed(stdin_input, project_dir)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
