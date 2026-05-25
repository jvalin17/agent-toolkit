#!/usr/bin/env python3
"""tdd_enforce.py — TDD reminder or strict block before file edits.

Runs as PreToolUse hook on Edit and Write tools.
Default (`tdd_mode: remind`): injects TDD reminder context.
Strict (`tdd_mode: strict`): blocks source edits until a test exists or
a test file was edited in the last 5 tool calls (F2.5).
"""

import json
import re
import sys
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_hook import get_config_value, load_gate_config
from session_state import load_state, STATE_FILENAME, SESSION_DIR

NON_CODE_EXTENSIONS = {
    ".md", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini",
    ".env", ".txt", ".csv", ".lock", ".svg", ".png", ".jpg",
}

TEST_NAME_PATTERNS = re.compile(
    r"^test_|_test\.|\.test\.|\.spec\.|Test\.|Spec\."
)

TEST_DIR_PATTERNS = re.compile(r"(^|/)(__tests__|tests?|spec)(/|$)")

CONFIG_PATTERNS = re.compile(
    r"\.config\.|^Makefile$|^Dockerfile$|^docker-compose|^setup\.|\.sh$"
)

TDD_EXEMPT_DIRS = re.compile(r"(^|/)(hooks|scripts|migrations|\.github|templates)(/|$)")

LAST_TEST_EDITS_WINDOW = 5


def make_hook_response(message: str) -> str:
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message,
            }
        }
    )


def make_block_response(reason: str) -> str:
    return json.dumps({"decision": "block", "reason": reason})


def find_test_file(file_path: Path, project_dir: Path) -> bool:
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


def is_skipped_file(file_path: Path, filename: str) -> bool:
    if file_path.suffix in NON_CODE_EXTENSIONS or filename.startswith(".env"):
        return True
    if TEST_NAME_PATTERNS.search(filename):
        return True
    if TEST_DIR_PATTERNS.search(str(file_path)):
        return True
    if CONFIG_PATTERNS.search(filename):
        return True
    if TDD_EXEMPT_DIRS.search(str(file_path)):
        return True
    return False


def recent_test_edit(project_dir: Path) -> bool:
    state_file = project_dir / SESSION_DIR / STATE_FILENAME
    state = load_state(state_file)
    return bool(state.last_test_edits)


def run_tdd_enforce(
    stdin_input: str,
    project_dir: Path,
) -> Tuple[int, str]:
    config = load_gate_config(project_dir)
    if not get_config_value(config, "tdd", True):
        return 0, ""

    tdd_mode = get_config_value(config, "tdd_mode", "remind")

    try:
        hook_input = json.loads(stdin_input)
        file_path_str = hook_input.get("tool_input", {}).get("file_path", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0, ""

    if not file_path_str:
        return 0, ""

    file_path = Path(file_path_str)
    filename = file_path.name

    if is_skipped_file(file_path, filename):
        return 0, ""

    if find_test_file(file_path, project_dir):
        return 0, ""

    if recent_test_edit(project_dir):
        return 0, ""

    if tdd_mode == "strict":
        message = (
            f"TDD STRICT: Write the test for {filename} first. "
            "Source edits are blocked until a test file exists."
        )
        return 0, make_block_response(message)

    message = (
        f"TDD CHECK: You are editing {filename} but no corresponding test file exists.\n\n"
        "FOR NEW FEATURES: Write the test FIRST with specific assertions, then implement.\n"
        "FOR BUG FIXES: Write a FAILING test that reproduces the bug FIRST, then fix the "
        "code to make it pass. The test stays as a permanent regression test.\n\n"
        "If this is a config/setup file that does not need tests, proceed."
    )
    return 0, make_hook_response(message)


def main() -> int:
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()
    exit_code, output = run_tdd_enforce(stdin_input, project_dir)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
