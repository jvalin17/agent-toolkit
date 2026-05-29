"""Mechanical code quality scoring — no agent self-reporting.

Scans the project for objective, measurable quality signals.
Called by finalize_report.py to compute evaluate dimension scores.
The agent cannot influence these scores — they come from the code itself.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List

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


def _count_long_functions(path: Path, threshold: int = 30) -> int:
    """Count functions longer than threshold lines using AST."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return 0
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = node.end_lineno - node.lineno + 1
            if length > threshold:
                count += 1
    return count


def check_code_quality(project_dir: Path) -> dict:
    """Scan for code quality signals. Returns score and details."""
    files = _python_files(project_dir)
    source_files = [f for f in files if not _is_test_file(f)]

    if not source_files:
        return {"score": 100, "long_functions": 0, "large_files": 0,
                "bare_excepts": 0, "source_files": 0}

    long_functions = 0
    large_files = 0
    bare_excepts = 0

    for path in source_files:
        long_functions += _count_long_functions(path)

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        line_count = content.count("\n")
        if line_count > 500:
            large_files += 1

        bare_excepts += len(re.findall(r"except\s*:", content))

    # Score: start at 100, deduct for issues
    score = 100
    score -= min(long_functions * 3, 30)   # -3 per long function, max -30
    score -= min(large_files * 10, 20)     # -10 per large file, max -20
    score -= min(bare_excepts * 5, 15)     # -5 per bare except, max -15

    return {
        "score": max(0, score),
        "long_functions": long_functions,
        "large_files": large_files,
        "bare_excepts": bare_excepts,
        "source_files": len(source_files),
    }


def check_security(project_dir: Path) -> dict:
    """Scan for security issues. Returns score and details."""
    files = _python_files(project_dir)

    shell_true_count = 0
    hardcoded_secrets = 0

    for path in files:
        if _is_test_file(path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        shell_true_count += len(SHELL_TRUE_PATTERN.findall(content))
        hardcoded_secrets += len(SECRET_PATTERNS.findall(content))

    score = 100
    score -= min(shell_true_count * 15, 40)   # -15 each, max -40
    score -= min(hardcoded_secrets * 20, 40)   # -20 each, max -40

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

    test_count = 0
    sloppy_assertions = 0

    for path in test_files:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        test_count += len(TEST_FUNCTION.findall(content))
        sloppy_assertions += len(SLOPPY_ASSERTIONS.findall(content))

    # Score based on: having tests, test count, no sloppy assertions
    score = 50  # base for having any tests

    # Bonus for test density (tests per source file)
    if source_files:
        density = test_count / max(len(source_files), 1)
        score += min(int(density * 15), 35)  # up to +35 for good density

    # Bonus for many tests
    score += min(test_count // 5, 10)  # +1 per 5 tests, max +10

    # Penalty for sloppy assertions
    score -= min(sloppy_assertions * 5, 20)

    return {
        "score": max(0, min(100, score)),
        "test_count": test_count,
        "test_files": len(test_files),
        "sloppy_assertions": sloppy_assertions,
        "source_files": len(source_files),
    }


def check_efficiency(project_dir: Path) -> dict:
    """Check for efficiency issues. Returns score and details."""
    files = _python_files(project_dir)
    source_files = [f for f in files if not _is_test_file(f)]

    if not source_files:
        return {"score": 90, "very_long_functions": 0, "source_files": 0}

    very_long_functions = 0  # > 50 lines
    for path in source_files:
        very_long_functions += _count_long_functions(path, threshold=50)

    score = 100
    score -= min(very_long_functions * 5, 30)

    return {
        "score": max(0, score),
        "very_long_functions": very_long_functions,
        "source_files": len(source_files),
    }


def score_codebase(project_dir: Path) -> dict:
    """Run all mechanical checks and return dimension scores.

    Returns dict with keys matching EVAL_DIMENSION_WEIGHTS:
    completeness, code_quality, security, test_quality, efficiency.
    All values are integers 0-100.
    """
    quality = check_code_quality(project_dir)
    security = check_security(project_dir)
    tests = check_test_quality(project_dir)
    efficiency = check_efficiency(project_dir)

    # Completeness is binary: do tests and lint pass?
    # This is handled separately by finalize_report (mechanical re-run).
    # Here we use test_quality as a proxy — having tests = complete.
    completeness = 100 if tests["test_count"] > 0 else 30

    return {
        "completeness": completeness,
        "code_quality": quality["score"],
        "security": security["score"],
        "test_quality": tests["score"],
        "efficiency": efficiency["score"],
    }
