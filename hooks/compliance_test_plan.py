"""Test plan validation and test redundancy detection.

Extracted from compliance.py. Contains:
- validate_test_plan: validate test plan JSON structure
- check_test_plan_coverage: verify test cases have matching test functions
- format_test_plan_summary: format plan as markdown for project-state.md
- detect_test_redundancy: scan test files for potentially redundant tests
"""

import re
from pathlib import Path
from typing import Any, Dict, List


# --- Test plan validation ----------------------------------------------------

TEST_PLAN_REQUIRED_KEYS = {"feature", "cases", "edge_cases", "created_at"}
TEST_CASE_REQUIRED_KEYS = {"id", "description", "test_file", "test_name"}


def validate_test_plan(plan: dict) -> List[str]:
    """Validate a test plan JSON structure.

    Returns list of error strings. Empty list = valid.
    """
    errors: List[str] = []

    for key in TEST_PLAN_REQUIRED_KEYS:
        if key not in plan:
            errors.append(f"missing required field: {key}")

    if "feature" in plan and not plan["feature"]:
        errors.append("feature must not be empty")

    cases = plan.get("cases", [])
    if not cases:
        errors.append("cases must contain at least one test case")

    for i, case in enumerate(cases):
        missing = TEST_CASE_REQUIRED_KEYS - set(case.keys())
        if missing:
            case_id = case.get("id", f"case[{i}]")
            errors.append(f"{case_id}: missing fields: {', '.join(sorted(missing))}")

    return errors


def check_test_plan_coverage(plan: dict, project_root: Path) -> List[str]:
    """Check that each test case in the plan has a corresponding test function.

    Returns list of missing-coverage strings. Empty = fully covered.
    """
    missing: List[str] = []

    for case in plan.get("cases", []):
        case_id = case.get("id", "?")
        test_file = case.get("test_file", "")
        test_name = case.get("test_name", "")

        file_path = project_root / test_file
        if not file_path.is_file():
            missing.append(f"{case_id}: test file not found: {test_file}")
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")
        if test_name not in content:
            missing.append(
                f"{case_id}: test function '{test_name}' not found in {test_file}"
            )

    return missing


def format_test_plan_summary(plan: dict) -> str:
    """Format a test plan as a markdown summary for project-state.md.

    The summary contains enough detail to reproduce the test cases.
    """
    feature = plan.get("feature", "unknown")
    created = plan.get("created_at", "")
    date = created[:10] if created else "unknown"

    lines = [f"### {feature} ({date})", ""]

    for case in plan.get("cases", []):
        case_id = case.get("id", "?")
        desc = case.get("description", "")
        test_file = case.get("test_file", "")
        test_name = case.get("test_name", "")
        lines.append(f"- {case_id}: {desc} → {test_file}:{test_name}")

    edge_cases = plan.get("edge_cases", [])
    if edge_cases:
        lines.append(f"- Edge cases: {', '.join(edge_cases)}")

    return "\n".join(lines)


# --- Test redundancy detection -----------------------------------------------

# Pattern to extract function-under-test from test name
# test_login_success → "login", test_add_numbers → "add"
TEST_NAME_PATTERN = re.compile(r"^test_(\w+?)_")

# Minimum group size to flag as potentially redundant
MIN_REDUNDANCY_GROUP = 3


def detect_test_redundancy(
    test_files: List[Path],
) -> List[Dict[str, Any]]:
    """Scan test files for potentially redundant tests.

    Groups test functions by the function they test (extracted from name).
    Flags groups with 3+ tests as potentially redundant — the reviewer
    agent makes the final judgment.

    Returns list of findings, each with group name, count, and test names.
    """
    if not test_files:
        return []

    # Collect all test function names with their file locations
    groups: Dict[str, List[Dict[str, str]]] = {}

    for file_path in test_files:
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped.startswith("def test_"):
                continue
            # Extract function name
            match = re.match(r"def (test_\w+)\s*\(", stripped)
            if not match:
                continue
            test_name = match.group(1)

            # Extract the function-under-test (first word after test_)
            group_match = TEST_NAME_PATTERN.match(test_name)
            if not group_match:
                continue
            group = group_match.group(1)

            if group not in groups:
                groups[group] = []
            groups[group].append({
                "test_name": test_name,
                "file": file_path.name,
            })

    # Flag groups with 3+ tests
    findings: List[Dict[str, Any]] = []
    for group, tests in sorted(groups.items()):
        if len(tests) >= MIN_REDUNDANCY_GROUP:
            findings.append({
                "group": group,
                "count": len(tests),
                "test_names": [t["test_name"] for t in tests],
                "files": list({t["file"] for t in tests}),
            })

    return findings
