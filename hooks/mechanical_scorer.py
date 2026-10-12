"""Mechanical code quality scoring — no agent self-reporting.

Scans the project for objective, measurable quality signals.
Called by finalize_report.py to compute evaluate dimension scores.
The agent cannot raise these scores — they come from the code itself.

Every threshold and penalty is a named constant below so the scoring policy
can be read (and tuned) in one place.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List

# --- Thresholds ---------------------------------------------------------------
LONG_FUNCTION_LINES = 30        # code_quality: a function longer than this is "long"
VERY_LONG_FUNCTION_LINES = 50   # efficiency: longer than this is "very long"
LARGE_FILE_LINES = 500          # code_quality: a module longer than this is "large"

# --- Code quality penalties (start at 100) ------------------------------------
PENALTY_PER_LONG_FUNCTION = 3
MAX_PENALTY_LONG_FUNCTIONS = 30
PENALTY_PER_LARGE_FILE = 10
MAX_PENALTY_LARGE_FILES = 20
PENALTY_PER_BARE_EXCEPT = 5
MAX_PENALTY_BARE_EXCEPTS = 15

# --- Security penalties (start at 100) ----------------------------------------
PENALTY_PER_SHELL_TRUE = 15
MAX_PENALTY_SHELL_TRUE = 40
PENALTY_PER_HARDCODED_SECRET = 20
MAX_PENALTY_HARDCODED_SECRETS = 40

# --- Test quality (start at TEST_BASE_SCORE, add bonuses, subtract penalties) --
TEST_BASE_SCORE = 50            # for having any tests at all
DENSITY_POINTS_PER_TEST_PER_FILE = 15
MAX_DENSITY_BONUS = 35
TESTS_PER_COUNT_BONUS_POINT = 5
MAX_COUNT_BONUS = 10
PENALTY_PER_SLOPPY_ASSERTION = 5
MAX_PENALTY_SLOPPY_ASSERTIONS = 20

# --- Efficiency (start at 100) -------------------------------------------------
PENALTY_PER_VERY_LONG_FUNCTION = 5
MAX_PENALTY_VERY_LONG_FUNCTIONS = 30
EFFICIENCY_SCORE_NO_SOURCE = 90  # nothing to measure; not a perfect 100

# --- Completeness proxy ---------------------------------------------------------
COMPLETENESS_WITH_TESTS = 100
COMPLETENESS_WITHOUT_TESTS = 30

# Patterns that indicate security problems
SHELL_TRUE_PATTERN = re.compile(r"shell\s*=\s*True")
SECRET_PATTERNS = re.compile(
    r"""(?:password|secret|api_key|apikey|token|auth_token)"""
    r"""\s*=\s*['"][^'"]{4,}['"]""",
    re.IGNORECASE,
)

# Sloppy test assertion patterns
SLOPPY_ASSERTIONS = re.compile(
    r"assert\s+True\b|assertTrue\s*\(\s*True\s*\)|"
    r"assertIsNotNone|toBeTruthy"
)

# Test function detection
TEST_FUNCTION = re.compile(r"^\s*def\s+(test_\w+)", re.MULTILINE)

BARE_EXCEPT = re.compile(r"except\s*:")


def _python_files(project_dir: Path) -> List[Path]:
    """Find all .py files, excluding hidden dirs and __pycache__."""
    results = []
    for path in project_dir.rglob("*.py"):
        parts = path.relative_to(project_dir).parts
        if any(p.startswith(".") or p == "__pycache__" for p in parts):
            continue
        results.append(path)
    return results


def _is_test_file(path: Path) -> bool:
    name = path.name
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or "tests/" in str(path)
        or "test/" in str(path)
    )


def _read_source(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _count_long_functions(path: Path, threshold: int = LONG_FUNCTION_LINES) -> int:
    """Count functions longer than threshold lines using AST."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return 0
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.end_lineno - node.lineno + 1 > threshold:
                count += 1
    return count


def _capped(count: int, per_item: int, cap: int) -> int:
    """Penalty or bonus for `count` items at `per_item` each, capped at `cap`."""
    return min(count * per_item, cap)


def check_code_quality(project_dir: Path) -> dict:
    """Scan for code quality signals. Returns score and details."""
    source_files = [f for f in _python_files(project_dir) if not _is_test_file(f)]
    if not source_files:
        return {"score": 100, "long_functions": 0, "large_files": 0,
                "bare_excepts": 0, "source_files": 0}

    long_functions = large_files = bare_excepts = 0
    for path in source_files:
        long_functions += _count_long_functions(path)
        content = _read_source(path)
        if content is None:
            continue
        if content.count("\n") > LARGE_FILE_LINES:
            large_files += 1
        bare_excepts += len(BARE_EXCEPT.findall(content))

    score = 100
    score -= _capped(long_functions, PENALTY_PER_LONG_FUNCTION, MAX_PENALTY_LONG_FUNCTIONS)
    score -= _capped(large_files, PENALTY_PER_LARGE_FILE, MAX_PENALTY_LARGE_FILES)
    score -= _capped(bare_excepts, PENALTY_PER_BARE_EXCEPT, MAX_PENALTY_BARE_EXCEPTS)

    return {
        "score": max(0, score),
        "long_functions": long_functions,
        "large_files": large_files,
        "bare_excepts": bare_excepts,
        "source_files": len(source_files),
    }


def check_security(project_dir: Path) -> dict:
    """Scan for security issues. Returns score and details."""
    shell_true_count = hardcoded_secrets = 0
    for path in _python_files(project_dir):
        if _is_test_file(path):
            continue
        content = _read_source(path)
        if content is None:
            continue
        shell_true_count += len(SHELL_TRUE_PATTERN.findall(content))
        hardcoded_secrets += len(SECRET_PATTERNS.findall(content))

    score = 100
    score -= _capped(shell_true_count, PENALTY_PER_SHELL_TRUE, MAX_PENALTY_SHELL_TRUE)
    score -= _capped(hardcoded_secrets, PENALTY_PER_HARDCODED_SECRET, MAX_PENALTY_HARDCODED_SECRETS)

    return {
        "score": max(0, score),
        "shell_true_count": shell_true_count,
        "hardcoded_secrets": hardcoded_secrets,
    }


def check_test_quality(project_dir: Path) -> dict:
    """Scan test files for quality signals. Returns score and details."""
    files = _python_files(project_dir)
    test_files = [f for f in files if _is_test_file(f)]
    source_files = [f for f in files if not _is_test_file(f)]

    if not test_files:
        return {"score": 0, "test_count": 0, "test_files": 0,
                "sloppy_assertions": 0, "source_files": len(source_files)}

    test_count = sloppy_assertions = 0
    for path in test_files:
        content = _read_source(path)
        if content is None:
            continue
        test_count += len(TEST_FUNCTION.findall(content))
        sloppy_assertions += len(SLOPPY_ASSERTIONS.findall(content))

    score = TEST_BASE_SCORE
    if source_files:
        density = test_count / len(source_files)
        score += min(int(density * DENSITY_POINTS_PER_TEST_PER_FILE), MAX_DENSITY_BONUS)
    score += min(test_count // TESTS_PER_COUNT_BONUS_POINT, MAX_COUNT_BONUS)
    score -= _capped(sloppy_assertions, PENALTY_PER_SLOPPY_ASSERTION, MAX_PENALTY_SLOPPY_ASSERTIONS)

    return {
        "score": max(0, min(100, score)),
        "test_count": test_count,
        "test_files": len(test_files),
        "sloppy_assertions": sloppy_assertions,
        "source_files": len(source_files),
    }


def check_efficiency(project_dir: Path) -> dict:
    """Check for efficiency issues. Returns score and details."""
    source_files = [f for f in _python_files(project_dir) if not _is_test_file(f)]
    if not source_files:
        return {"score": EFFICIENCY_SCORE_NO_SOURCE, "very_long_functions": 0, "source_files": 0}

    very_long_functions = sum(
        _count_long_functions(path, threshold=VERY_LONG_FUNCTION_LINES) for path in source_files
    )
    score = 100 - _capped(
        very_long_functions, PENALTY_PER_VERY_LONG_FUNCTION, MAX_PENALTY_VERY_LONG_FUNCTIONS
    )

    return {
        "score": max(0, score),
        "very_long_functions": very_long_functions,
        "source_files": len(source_files),
    }


def score_codebase(project_dir: Path) -> dict:
    """Run all mechanical checks and return dimension scores.

    Returns dict with keys matching EVAL_DIMENSION_WEIGHTS:
    completeness, code_quality, security, test_quality, efficiency.
    All values are integers 0-100. Completeness here is only a proxy
    (tests exist); finalize_report adjusts it from the real test/lint re-run.
    """
    quality = check_code_quality(project_dir)
    security = check_security(project_dir)
    tests = check_test_quality(project_dir)
    efficiency = check_efficiency(project_dir)
    completeness = COMPLETENESS_WITH_TESTS if tests["test_count"] > 0 else COMPLETENESS_WITHOUT_TESTS

    return {
        "completeness": completeness,
        "code_quality": quality["score"],
        "security": security["score"],
        "test_quality": tests["score"],
        "efficiency": efficiency["score"],
    }
