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

# Skills that authorize code changes — mirrors skill_enforce.py CODE_CHANGE_SKILLS
CODE_CHANGE_SKILLS = {
    "implementation", "build", "debug_tool", "fix", "refactor",
    "setup", "explore",
}


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


def _track_skill_state(project_dir: Path, skill: str) -> None:
    """Write skill_state.json so skill_enforce.py can authorize edits.

    Called for code-change skills invoked via slash commands.
    Gated skills (precommit, evaluate, etc.) do NOT overwrite — they
    don't authorize code edits.
    """
    try:
        scratch_dir = project_dir / ".scratch"
        scratch_dir.mkdir(exist_ok=True)
        state_file = scratch_dir / "skill_state.json"
        state_file.write_text(json.dumps({"last_skill_routed": skill}))
    except OSError:
        pass


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

    if not skill:
        return 0, ""

    # Track code-change skills so skill_enforce.py can authorize edits.
    # This covers slash-command invocations that route_to_skill.py misses.
    if skill in CODE_CHANGE_SKILLS:
        _track_skill_state(project_dir, skill)

    # F3.2: After /implementation, inject demo prompt (new features only)
    if skill == "implementation":
        message = (
            "If this was a new feature (not a fix or refactor): "
            "DEMO with real data before committing. "
            "Ask the user for sample data if you don't have any. "
            "Skip this for bug fixes and refactors."
        )
        return 0, make_hook_response(message)

    if skill not in GATED_SKILLS:
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
