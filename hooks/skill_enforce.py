#!/usr/bin/env python3
"""skill_enforce.py — Enforce skill workflows during code edits.

PreToolUse hook on Edit and Write tools. Two behaviors:

1. REMIND (all modes except minimal): Injects workflow reminder on every
   source code edit — even when a skill IS active. Prevents agents from
   "slipping out" of /implementation mid-task.

2. BLOCK (default, standard, safe): Denies source code edits when NO
   skill workflow is active. Forces agents to invoke a skill first.

Exempt: non-code files (.md, .json, .yml, config), hooks/, scripts/, test files
"""

import json
import re
import sys
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_hook import get_config_value, load_gate_config
from mode_resolver import resolve_mode_from_config

# Modes where no-skill edits are blocked (not just reminded)
BLOCK_MODES = {"default", "standard", "safe"}

NON_CODE_EXTENSIONS = {
    ".md", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini",
    ".env", ".txt", ".csv", ".lock", ".svg", ".png", ".jpg",
    ".gitignore", ".sh",
}

EXEMPT_PATHS = re.compile(
    r"(^|/)(hooks|scripts|\.github|\.scratch|\.session|\.gates|reports|roles|shared|templates|docs|architecture|requirements)(/|$)"
)

TEST_PATTERNS = re.compile(
    r"(^|/)(__tests__|tests?|spec|test_|_test\.|\.test\.|\.spec\.)"
)

# Skills that authorize code changes
# "build" is the intent key written by route_to_skill.py for /implementation
CODE_CHANGE_SKILLS = {
    "implementation", "build", "debug_tool", "fix", "refactor",
    "setup", "explore",  # explore is read-only but setup writes configs
}

# Skills that should run BEFORE code changes
PRE_CODE_SKILLS = {
    "requirements", "architecture",
}


def _is_code_file(file_path: str) -> bool:
    """Check if this is a code file (not config, docs, or tests)."""
    path = Path(file_path)

    # Non-code extensions
    if path.suffix.lower() in NON_CODE_EXTENSIONS:
        return False

    # Exempt directories
    if EXEMPT_PATHS.search(file_path):
        return False

    # Test files — allowed without skill
    if TEST_PATTERNS.search(file_path):
        return False

    return True


def _check_skill_active(project_dir: Path) -> Tuple[bool, str]:
    """Check if a code-change-authorizing skill was recently invoked.

    Reads session state to see if route_to_skill injected a skill context.
    Also checks .session/state.json for recent skill invocations.
    """
    # Check .scratch/skill_state.json for last routed skill
    skill_state = project_dir / ".scratch" / "skill_state.json"
    if skill_state.is_file():
        try:
            state = json.loads(skill_state.read_text())
            last_skill = state.get("last_skill_routed", "")
            if last_skill in CODE_CHANGE_SKILLS:
                return True, last_skill
            if last_skill in PRE_CODE_SKILLS:
                return False, last_skill
        except (json.JSONDecodeError, OSError):
            pass

    # No skill detected
    return False, "none"


SKILL_REMINDER = (
    "IMPLEMENTATION REMINDER: You are in a skill workflow. Stay on track:\n"
    "- Follow the slab structure (test first → implement → verify)\n"
    "- Do NOT skip steps or write code without a failing test\n"
    "- When done with this slab, update project-state.md"
)

NO_SKILL_MESSAGE = (
    "SKILL REQUIRED: You are editing code without following a skill workflow. "
    "Before making code changes:\n"
    "- New feature → run /requirements then /implementation\n"
    "- Bug fix → run /debug_tool\n"
    "- Refactor → run /implementation in refactor mode\n"
    "- Architecture change → run /architecture first\n"
    "Do NOT edit code directly. Follow the skill workflow."
)


def _make_remind(message: str) -> str:
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    })


def _make_block(message: str) -> str:
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "reason": message,
        }
    })


def run_skill_enforce(
    stdin_input: str,
    project_dir: Path,
) -> Tuple[int, str]:
    """Check if code edit is authorized by an active skill."""
    config = load_gate_config(project_dir)

    # Explicit "off" override always wins
    explicit = get_config_value(config, "skill_enforce", None)
    if explicit == "off":
        return 0, ""

    # Resolve mode
    mode = resolve_mode_from_config(config)

    # Minimal mode: no enforcement
    if mode.name == "minimal":
        return 0, ""

    try:
        event = json.loads(stdin_input)
    except (json.JSONDecodeError, TypeError):
        return 0, ""

    tool_input = event.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return 0, ""

    # Skip non-code files
    if not _is_code_file(file_path):
        return 0, ""

    # Check if a skill is active
    skill_active, skill_name = _check_skill_active(project_dir)

    # Determine block vs remind for no-skill case
    # Explicit override takes precedence, then mode-based
    should_block = mode.name in BLOCK_MODES
    if explicit == "block":
        should_block = True
    elif explicit == "remind":
        should_block = False

    if skill_active:
        # Skill is active — inject anti-drift reminder (never block)
        return 0, _make_remind(SKILL_REMINDER)

    # No skill active — block or remind
    if should_block:
        return 0, _make_block(NO_SKILL_MESSAGE)

    return 0, _make_remind(NO_SKILL_MESSAGE)


def main() -> int:
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()
    exit_code, output = run_skill_enforce(stdin_input, project_dir)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
