"""Git diff analysis — detect untested functions, noqa abuse, UI changes.

Extracted from compliance.py. Contains:
- check_diff_for_untested_functions: scan diff for new functions without tests
- check_diff_for_noqa_in_tests: detect noqa suppression in test files
- detect_ui_files_in_diff: find UI/frontend files in a diff
- check_diff_for_ui_without_e2e: check UI changes without E2E test updates
"""

import re
from pathlib import Path
from typing import Dict, List, Optional


# Patterns for function/method definitions (added lines only)
FUNCTION_DEF_PATTERNS = [
    # Python: def func_name(
    re.compile(r"^\+\s*def\s+(\w+)\s*\("),
    # JS/TS: function funcName(  or  const funcName = (  or  funcName(
    re.compile(r"^\+\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\("),
    # Go: func FuncName(
    re.compile(r"^\+\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\("),
    # Rust: fn func_name(
    re.compile(r"^\+\s*(?:pub\s+)?fn\s+(\w+)\s*\("),
    # Java/C#: public void methodName(
    re.compile(r"^\+\s*(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)*(\w+)\s*\("),
]

# Dunder / magic methods to ignore
DUNDER_RE = re.compile(r"^__\w+__$")

# Files/dirs exempt from TDD diff check
DIFF_TDD_EXEMPT_DIRS = re.compile(
    r"(^|/)(hooks|scripts|migrations|\.github|\.agent-toolkit|templates|config|docs|static|demos)(/|$)"
)

DIFF_TEST_FILE_PATTERN = re.compile(
    r"(test_|_test\.|\.test\.|\.spec\.|tests/|__tests__/|spec/)",
    re.IGNORECASE,
)

# Documentation and data files: a `def` inside a Markdown code example is prose,
# not a source function that needs a test.
DIFF_NON_CODE_FILE_PATTERN = re.compile(
    r"\.(md|markdown|rst|txt|json|ya?ml|toml|html?|csv)$",
    re.IGNORECASE,
)

# UI file patterns — detect frontend component/style changes
# Two conditions: file has a UI extension, OR file has a UI extension AND lives in a UI directory.
# Directory-only matches (components/README.md) are excluded by requiring an extension match.
UI_FILE_EXTENSIONS = re.compile(
    r"\.(tsx|jsx|vue|svelte|css|scss|less|styl"
    r"|swift|xib|storyboard"  # iOS
    r"|xml|kt)$",  # Android layouts + Kotlin UI
    re.IGNORECASE,
)
UI_DIR_PATTERN = re.compile(
    r"components?/|pages?/|views?/|screens?/|layouts?/"
    r"|styles?/|theme/",
    re.IGNORECASE,
)

# E2E test patterns — detect existing Playwright/Cypress tests
E2E_TEST_PATTERN = re.compile(
    r"\.e2e\.\w+$|e2e/|cypress/|playwright/|__e2e__/",
    re.IGNORECASE,
)


def detect_ui_files_in_diff(diff_text: str) -> List[str]:
    """Find UI/frontend files in a git diff. Returns list of file paths.

    A file is considered UI if it has a UI extension (.tsx, .jsx, .vue, .css, etc.).
    Files in UI directories (components/, pages/) are included only if they also
    have a UI extension — prevents matching README.md in components/.
    """
    if not diff_text.strip():
        return []
    ui_files = []
    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match:
                filepath = match.group(1)
                if DIFF_TEST_FILE_PATTERN.search(filepath):
                    continue  # skip test files
                if UI_FILE_EXTENSIONS.search(filepath):
                    ui_files.append(filepath)
    return ui_files


def check_diff_for_ui_without_e2e(diff_text: str) -> List[str]:
    """Check if UI files changed without corresponding E2E test updates.

    Returns list of warning strings. Empty = all UI changes have E2E coverage.
    """
    ui_files = detect_ui_files_in_diff(diff_text)
    if not ui_files:
        return []

    # Check if any E2E test files were also changed
    e2e_updated = False
    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match and E2E_TEST_PATTERN.search(match.group(1)):
                e2e_updated = True
                break

    if e2e_updated:
        return []

    return [
        f"UI component '{Path(f).name}' changed without E2E test update"
        for f in ui_files[:5]  # cap at 5 to avoid noise
    ]


def check_diff_for_untested_functions(diff_text: str) -> List[str]:
    """Scan a unified diff for new functions/methods without corresponding tests.

    Returns list of warning strings, one per untested function.
    Empty list = all new functions have tests (or no new functions).
    """
    if not diff_text.strip():
        return []

    # Parse diff into per-file sections
    current_file = None
    source_functions: Dict[str, List[str]] = {}  # file -> [func_names]
    test_functions: List[str] = []

    for line in diff_text.split("\n"):
        # Track which file we're in
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            if match:
                current_file = match.group(1)
            continue

        if current_file is None:
            continue

        # Only look at added lines
        if not line.startswith("+"):
            continue

        is_test_file = bool(DIFF_TEST_FILE_PATTERN.search(current_file))
        is_exempt = bool(DIFF_TDD_EXEMPT_DIRS.search(current_file)) or bool(
            DIFF_NON_CODE_FILE_PATTERN.search(current_file)
        )

        for pattern in FUNCTION_DEF_PATTERNS:
            m = pattern.match(line)
            if m:
                func_name = m.group(1)
                # Skip dunder methods
                if DUNDER_RE.match(func_name):
                    break
                if is_test_file:
                    test_functions.append(func_name)
                elif not is_exempt:
                    if current_file not in source_functions:
                        source_functions[current_file] = []
                    source_functions[current_file].append(func_name)
                break

    # Check each source function for a corresponding test
    warnings = []
    for filepath, funcs in source_functions.items():
        for func in funcs:
            # Look for test_<func> or <func> mentioned in any test function name
            has_test = any(
                func in test_name or func.lower() in test_name.lower()
                for test_name in test_functions
            )
            if not has_test:
                warnings.append(
                    f"{filepath}: new function '{func}' has no corresponding test"
                )

    return warnings


def check_diff_for_noqa_in_tests(diff_text: str) -> List[str]:
    """Scan a unified diff for added # noqa comments in test files.

    Adding noqa to test files is almost always a sign the agent is fighting
    the linter (e.g., renaming snake_case to camelCase then suppressing N802)
    instead of fixing the actual issue.

    Returns list of warning strings, one per offending line.
    """
    if not diff_text.strip():
        return []

    current_file: Optional[str] = None
    warnings: List[str] = []

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            current_file = match.group(1) if match else None
            continue

        if current_file is None:
            continue

        # Only check added lines in test files
        if not line.startswith("+"):
            continue
        # Skip nested diff content (e.g., diff examples inside test strings)
        if line.startswith("++"):
            continue
        if not DIFF_TEST_FILE_PATTERN.search(current_file):
            continue

        # Match actual code with # noqa directive at end-of-line
        # (not strings/docstrings that mention noqa as content)
        code = line[1:]  # strip leading +
        if re.search(r"[^\"']\s+#\s*noqa\b", code) and not code.lstrip().startswith(("#", '"""', "'''")):
            warnings.append(
                f"{current_file}: added '# noqa' suppression in test file — "
                "fix the lint issue instead of suppressing it"
            )

    return warnings


# Assertions that cannot fail, on added lines in test files. Expected values
# must come from an independent source (a literal, a worked example, the
# spec); an assertion that compares a thing to itself, or asserts a constant
# truth, passes by construction and proves nothing.
TAUTOLOGY_PATTERNS = [
    re.compile(r"^\s*assert\s+True\s*(#.*)?$"),
    re.compile(r"assertTrue\(\s*True\s*\)"),
    re.compile(r"expect\(\s*true\s*\)\.(toBe\(\s*true\s*\)|toBeTruthy\(\))"),
    re.compile(r"^\s*assert\s+(?P<a>[^=!<>]+?)\s*==\s*(?P=a)\s*(#.*)?$"),
    re.compile(r"expect\(\s*(?P<e>[^()]+?)\s*\)\.(toBe|toEqual|toStrictEqual)\(\s*(?P=e)\s*\)"),
]


def check_diff_for_tautological_tests(diff_text: str) -> List[str]:
    """Scan a unified diff for added test assertions that cannot fail.

    Returns one "<file>: <line>" string per offending added line in a test file.
    """
    if not diff_text.strip():
        return []

    current_file: Optional[str] = None
    findings: List[str] = []

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            match = re.search(r"b/(.+)$", line)
            current_file = match.group(1) if match else None
            continue
        if current_file is None or not line.startswith("+") or line.startswith("++"):
            continue
        if not DIFF_TEST_FILE_PATTERN.search(current_file):
            continue
        content = line[1:]
        if any(pattern.search(content) for pattern in TAUTOLOGY_PATTERNS):
            findings.append(f"{current_file}: {content.strip()}")
    return findings
