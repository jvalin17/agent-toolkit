"""Strict mode helpers — drift detection, pattern matching, integrity checks.

Extracted from session_monitor.py to keep each module focused on one concern.
"""

import re
from pathlib import Path

# Real-system query patterns (strict mode drift detection)
REAL_SYSTEM_QUERY_PATTERNS = re.compile(
    r"\b(curl|wget|httpie|grpcurl|postman)\b"
    r"|\bhttp\s+(GET|POST|PUT|DELETE|PATCH)\b"
    r"|\b(psql|mysql|sqlite3|mongosh)\b"
    r"|\b(SELECT|INSERT|UPDATE|DELETE)\s+"
    r"|\bdocker\s+exec\b.*\b(psql|mysql|mongo|redis)",
    re.IGNORECASE,
)

# Test runner patterns
TEST_RUNNER_PATTERNS = re.compile(
    r"\b(pytest|py\.test|python3?\s+-m\s+pytest)\b"
    r"|\b(jest|vitest|mocha)\b"
    r"|\bgo\s+test\b"
    r"|\bcargo\s+test\b"
    r"|\bnpm\s+(run\s+)?test\b"
    r"|\byarn\s+test\b",
    re.IGNORECASE,
)

# Test failure indicators in output
TEST_FAILURE_PATTERNS = re.compile(
    r"\bFAILED\b|\bFAILURE\b|\bERROR\b.*test"
    r"|\bfailed\b.*\btests?\b"
    r"|\bAssertionError\b"
    r"|\bExpect.*received\b",
    re.IGNORECASE,
)


def is_real_system_query(command: str) -> bool:
    """Check if a Bash command queries a real system (DB, API, etc.)."""
    if not command:
        return False
    return bool(REAL_SYSTEM_QUERY_PATTERNS.search(command))


def is_test_command(command: str) -> bool:
    """Check if a Bash command runs a test suite."""
    if not command:
        return False
    return bool(TEST_RUNNER_PATTERNS.search(command))


def is_test_failure(output: str) -> bool:
    """Check if tool output indicates test failure."""
    if not output:
        return False
    return bool(TEST_FAILURE_PATTERNS.search(output))


def is_test_file(file_path: str) -> bool:
    """Check if a file path is a test file."""
    if not file_path:
        return False
    name = Path(file_path).name
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".test.js")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.js")
        or "/tests/" in file_path
        or "/test/" in file_path
        or "/__tests__/" in file_path
    )


def detect_patch_forward(sequence: list) -> bool:
    """Detect patch-forward pattern in tool sequence.

    Pattern: test failure -> Edit/Write source file with no investigation between.
    Investigation = Read, Grep, or real-system query (Bash with query pattern).
    """
    if len(sequence) < 2:
        return False

    # Walk backward from the last entry
    last = sequence[-1]
    if last.get("tool") not in ("Edit", "Write"):
        return False

    # If editing a test file, not patch-forward
    if is_test_file(last.get("file_path", "")):
        return False

    # Look backward for test failure, checking for investigation between
    for i in range(len(sequence) - 2, -1, -1):
        entry = sequence[i]

        # Found investigation — not patch-forward
        if entry.get("tool") in ("Read", "Grep"):
            return False
        if entry.get("was_query"):
            return False

        # Found test failure — this is patch-forward
        if entry.get("was_test") and entry.get("failed"):
            return True

        # Found non-test, non-investigation tool — stop searching
        if entry.get("tool") not in ("Edit", "Write"):
            return False

    return False


def compute_drift_score(
    exchanges_since_query: int,
    patch_forward_count: int,
    slabs_without_data: int,
) -> float:
    """Compute drift score from counters. Returns 0.0 to 1.0.

    Formula from requirements/strict-mode.md:
      min(exchanges/10, 1.0) * 0.4 + min(patches/3, 1.0) * 0.4 + min(slabs/2, 1.0) * 0.2
    """
    return (
        min(exchanges_since_query / 10, 1.0) * 0.4
        + min(patch_forward_count / 3, 1.0) * 0.4
        + min(slabs_without_data / 2, 1.0) * 0.2
    )
