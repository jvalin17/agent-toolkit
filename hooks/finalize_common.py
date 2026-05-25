"""Shared constants and helpers for finalize_report."""

from __future__ import annotations

import re
import sys

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

EVAL_DIMENSION_WEIGHTS: dict[str, float] = {
    "completeness": 0.30,
    "code_quality": 0.25,
    "security": 0.20,
    "test_quality": 0.15,
    "efficiency": 0.10,
}


def fail(msg: str, code: int = 2) -> "NoReturn":  # type: ignore[name-defined]
    sys.stderr.write(f"finalize_report: {msg}\n")
    sys.exit(code)


def trim_detail(detail: str, limit: int = 200) -> str:
    if not detail:
        return "—"
    s = detail.replace("\n", " ").replace("|", "\\|").strip()
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s


def inline(prefix: str, value) -> str:
    if not value:
        return ""
    return f"{prefix}{str(value).strip()}"
