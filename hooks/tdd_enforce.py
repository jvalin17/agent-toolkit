#!/usr/bin/env python3
"""tdd_enforce.py — Reminds agent about TDD before every file edit.

Runs as PreToolUse hook on Edit and Write tools.
Checks if the file being edited is a source file (not a test).
If so, and no corresponding test exists, injects TDD reminder context.

Does NOT block — blocking Edit would break too many legitimate workflows.
Replaces tdd-enforce.sh.
"""

import json
import re
import sys
from pathlib import Path
from typing import Tuple

# Ensure sibling modules are importable regardless of CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_hook import get_config_value, load_gate_config

# File extensions that are not code — skip these
NON_CODE_EXTENSIONS = {
    ".md", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini",
    ".env", ".txt", ".csv", ".lock", ".svg", ".png", ".jpg",
}

# Test file name patterns
TEST_NAME_PATTERNS = re.compile(
    r"^test_|_test\.|\.test\.|\.spec\.|Test\.|Spec\."
)

# Test directory patterns
TEST_DIR_PATTERNS = re.compile(r"(^|/)(__tests__|tests?|spec)(/|$)")

# Config/setup file patterns
CONFIG_PATTERNS = re.compile(
    r"\.config\.|^Makefile$|^Dockerfile$|^docker-compose|^setup\.|\.sh$"
)


def make_hook_response(message: str) -> str:
    """Build Claude Code PreToolUse hook JSON response."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message,
            }
        }
    )


def find_test_file(file_path: Path, project_dir: Path) -> bool:
    """Check if a corresponding test file exists for the given source file."""
    basename = file_path.stem
    extension = file_path.suffix
    source_dir = file_path.parent

    test_patterns = [
        f"test_{basename}{extension}",
        f"{basename}_test{extension}",
        f"{basename}.test{extension}",
        f"{basename}.spec{extension}",
        f"{basename}Test{extension}",
        f"{basename}Spec{extension}",
    ]

    search_dirs = [
        source_dir,
        source_dir.parent / "tests",
        source_dir.parent / "test",
        source_dir.parent / "__tests__",
        project_dir / "tests",
        project_dir / "test",
        project_dir / "__tests__",
    ]

    for test_name in test_patterns:
        for search_dir in search_dirs:
            if (search_dir / test_name).is_file():
                return True
    return False


def run_tdd_enforce(
    stdin_input: str,
    project_dir: Path,
) -> Tuple[int, str]:
    """Check for TDD compliance before file edit. Returns (exit_code, output)."""
    config = load_gate_config(project_dir)
    if not get_config_value(config, "tdd", True):
        return 0, ""

    try:
        hook_input = json.loads(stdin_input)
        file_path_str = hook_input.get("tool_input", {}).get("file_path", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0, ""

    if not file_path_str:
        return 0, ""

    file_path = Path(file_path_str)
    filename = file_path.name

    # Skip non-code files (check suffix and .env* prefix)
    if file_path.suffix in NON_CODE_EXTENSIONS or filename.startswith(".env"):
        return 0, ""

    # Skip if this IS a test file
    if TEST_NAME_PATTERNS.search(filename):
        return 0, ""

    # Skip if in a test directory
    if TEST_DIR_PATTERNS.search(str(file_path)):
        return 0, ""

    # Skip config/setup files
    if CONFIG_PATTERNS.search(filename):
        return 0, ""

    # Source file — check if corresponding test exists
    if find_test_file(file_path, project_dir):
        return 0, ""

    # No test found — inject TDD reminder
    message = (
        f"TDD CHECK: You are editing {filename} but no corresponding test file exists.\n\n"
        "FOR NEW FEATURES: Write the test FIRST with specific assertions, then implement.\n"
        "FOR BUG FIXES: Write a FAILING test that reproduces the bug FIRST, then fix the "
        "code to make it pass. The test stays as a permanent regression test.\n\n"
        "If this is a config/setup file that does not need tests, proceed."
    )

    return 0, make_hook_response(message)


def main() -> int:
    """Entry point — reads hook input from stdin."""
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()
    exit_code, output = run_tdd_enforce(stdin_input, project_dir)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
