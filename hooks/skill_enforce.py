#!/usr/bin/env python3
"""skill_enforce.py — Block code edits without an active skill workflow.

PreToolUse hook on Edit and Write tools. Ensures the agent is following
a skill (/implementation, /debug, /architecture, /requirements) before
making code changes. Prevents the LLM from skipping skill workflows.

Modes:
  remind (default): injects warning context
  block: denies the tool call

Exempt: non-code files (.md, .json, .yml, config), hooks/, scripts/, test files
"""

import json
import re
import sys
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_hook import get_config_value, load_gate_config

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
CODE_CHANGE_SKILLS = {
    "implementation", "debug", "fix", "refactor",
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

    # Check .scratch for recent precommit/skill findings
    scratch = project_dir / ".scratch"
    if scratch.is_dir():
        try:
            if any(scratch.iterdir()):
                return True, "scratch-active"
        except OSError:
            pass

    # No skill detected — but don't block if we can't determine
    # (fail open to avoid breaking workflows)
    return True, "unknown"


def run_skill_enforce(
    stdin_input: str,
    project_dir: Path,
) -> Tuple[int, str]:
    """Check if code edit is authorized by an active skill."""
    config = load_gate_config(project_dir)

    # Enforcement level determined by:
    # 1. Explicit: "skill_enforce": "block" / "remind" / "off"
    # 2. Mode-based: "strict" mode → block, "normal" → remind
    skill_enforce_mode = get_config_value(config, "skill_enforce", None)
    if skill_enforce_mode is None:
        mode = get_config_value(config, "mode", "normal")
        skill_enforce_mode = "block" if mode == "strict" else "remind"
    if skill_enforce_mode == "off":
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

    if skill_active:
        return 0, ""

    # Skill not active — warn or block
    message = (
        "SKILL REQUIRED: You are editing code without following a skill workflow. "
        "Before making code changes:\n"
        "- New feature → run /requirements then /implementation\n"
        "- Bug fix → run /debug\n"
        "- Refactor → run /implementation in refactor mode\n"
        "- Architecture change → run /architecture first\n"
        "Do NOT edit code directly. Follow the skill workflow."
    )

    if skill_enforce_mode == "block":
        output = json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "reason": message,
            }
        })
        return 0, output

    # Default: remind
    output = json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    })
    return 0, output


def main() -> int:
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()
    exit_code, output = run_skill_enforce(stdin_input, project_dir)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
