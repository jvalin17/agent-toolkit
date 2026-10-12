"""Findings JSON schema validation for finalize_report."""

from __future__ import annotations

import json
from pathlib import Path

from finalize_common import EVAL_DIMENSION_WEIGHTS, SLUG_RE, fail


def read_findings(path: Path) -> dict:
    if not path.is_file():
        fail(f"findings file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"findings is not valid JSON: {exc}")
    if not isinstance(data, dict):
        fail("findings root must be a JSON object")
    return data


def _require(d: dict, key: str, kind, context: str) -> object:
    if key not in d:
        fail(f"{context}: missing required key '{key}'")
    value = d[key]
    if not isinstance(value, kind):
        fail(
            f"{context}: key '{key}' must be {kind.__name__}, "
            f"got {type(value).__name__}"
        )
    return value


def _validate_slug(data: dict, skill_name: str) -> None:
    skill = _require(data, "skill", str, "findings")
    if skill != skill_name:
        fail(f"findings.skill must be '{skill_name}', got '{skill}'")

    slug = _require(data, "slug", str, "findings")
    if not SLUG_RE.match(slug):
        fail(
            f"findings.slug '{slug}' is not a valid slug "
            "(lowercase, alphanumeric, dashes, 1-64 chars)"
        )


def _require_nonneg_int(d: dict, key: str, context: str) -> int:
    val = _require(d, key, int, context)
    if val < 0:
        fail(f"{context}: '{key}' must be >= 0 (got {val})")
    return val


def validate_precommit_findings(data: dict) -> dict:
    skill = _require(data, "skill", str, "findings")
    if skill != "precommit":
        fail(f"findings.skill must be 'precommit', got '{skill}'")

    slug = _require(data, "slug", str, "findings")
    if not SLUG_RE.match(slug):
        fail(
            f"findings.slug '{slug}' is not a valid slug "
            "(lowercase, alphanumeric, dashes, 1-64 chars)"
        )

    instr = _require(data, "instructions", dict, "findings")
    addressed = _require(instr, "addressed", int, "findings.instructions")
    total = _require(instr, "total", int, "findings.instructions")
    if addressed < 0 or total < 0 or addressed > total:
        fail(
            "findings.instructions: 'addressed' must be 0..total "
            f"(got addressed={addressed}, total={total})"
        )

    rules = _require(data, "rules", dict, "findings")
    _require(rules, "violations", int, "findings.rules")

    readme = _require(data, "readme", dict, "findings")
    _require(readme, "passed", bool, "findings.readme")

    tm = _require(data, "tests_meaningful", dict, "findings")
    tm_result = _require(tm, "result", str, "findings.tests_meaningful")
    if tm_result not in ("verified", "sloppy", "skipped"):
        fail(
            "findings.tests_meaningful.result must be one of "
            f"verified|sloppy|skipped (got '{tm_result}')"
        )

    appv = _require(data, "app_verification", dict, "findings")
    appv_status = _require(appv, "status", str, "findings.app_verification")
    if appv_status not in ("done", "pending", "na"):
        fail(
            "findings.app_verification.status must be done|pending|na "
            f"(got '{appv_status}')"
        )

    return data


def validate_evaluate_findings(data: dict) -> dict:
    """Validate evaluate findings.

    The hook computes scores mechanically via mechanical_scorer.py. Agent
    `dimensions` are optional; when present each must be an int 0-100 for a
    known dimension, and they can only LOWER the mechanical score
    (see merge_dimension_scores).
    """
    skill = _require(data, "skill", str, "findings")
    if skill != "evaluate":
        fail(f"findings.skill must be 'evaluate', got '{skill}'")

    slug = _require(data, "slug", str, "findings")
    if not SLUG_RE.match(slug):
        fail(
            f"findings.slug '{slug}' is not a valid slug "
            "(lowercase, alphanumeric, dashes, 1-64 chars)"
        )

    _require(data, "topic", str, "findings")

    dimensions = data.get("dimensions")
    if dimensions is not None:
        if not isinstance(dimensions, dict):
            fail("findings.dimensions must be an object of dimension → integer 0-100")
        for key, value in dimensions.items():
            if key not in EVAL_DIMENSION_WEIGHTS:
                fail(f"findings.dimensions has unknown dimension '{key}'")
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
                fail(f"findings.dimensions.{key} must be an integer 0-100, got {value!r}")

    return data


def merge_dimension_scores(mechanical: dict, agent: dict | None) -> dict:
    """Per dimension, the lower of the mechanical and agent-reported score.

    Mechanical checks are grep heuristics; the agent reads the code. Either
    may spot a problem the other cannot, so a dimension takes the worse of the
    two. The agent can never raise a score above what the mechanics found.
    """
    merged = dict(mechanical)
    if not agent:
        return merged
    for key in EVAL_DIMENSION_WEIGHTS:
        if key in agent and key in merged:
            merged[key] = min(int(merged[key]), int(agent[key]))
    return merged


def validate_reviewer_findings(data: dict) -> dict:
    _validate_slug(data, "reviewer")
    _require(data, "topic", str, "findings")
    counts = _require(data, "findings", dict, "findings")
    for key in ("high", "medium", "low"):
        _require_nonneg_int(counts, key, f"findings.{key}")

    areas = data.get("areas_reviewed", [])
    if areas is not None and not isinstance(areas, list):
        fail("findings.areas_reviewed must be a list if present")
    if isinstance(areas, list):
        for item in areas:
            if not isinstance(item, str):
                fail("findings.areas_reviewed items must be strings")

    return data


def validate_assess_findings(data: dict) -> dict:
    _validate_slug(data, "assess")
    _require(data, "topic", str, "findings")
    counts = _require(data, "findings", dict, "findings")
    for key in ("fix_now", "consider", "good"):
        _require_nonneg_int(counts, key, f"findings.{key}")

    return data


def compute_evaluate_score(dimensions: dict) -> int:
    total = sum(dimensions[k] * w for k, w in EVAL_DIMENSION_WEIGHTS.items())
    return round(total)


def grade_letter(score: int) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 85:
        return "B+"
    if score >= 80:
        return "B"
    if score >= 75:
        return "C+"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"
