#!/usr/bin/env python3
"""finalize_report.py — Hook-owned writer for skill reports.

The toolkit's report-protection model (G-REPORT-1) blocks agents from
writing into reports/. This hook is the ONLY allowed writer: it accepts
an agent-produced findings.json, re-runs the mechanical claims itself
(so the agent cannot fabricate command results), and composes a canonical
report file in reports/<skill>/.

Usage:
    python3 hooks/finalize_report.py <skill> <findings_json_path>

Supported skills: precommit, evaluate, reviewer, assess

Exit codes:
    0 — report written, gate-ready
    1 — report written, BLOCKED (mechanical or finding failures)
    2 — validation error (bad findings.json, unknown skill)

Layout:
    finalize_checks.py    shared checks + report/gate I/O
    finalize_precommit.py precommit gate
    this module           evaluate / reviewer / assess gates + CLI dispatch
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import finalize_checks as checks  # noqa: E402
from finalize_checks import (  # noqa: E402,F401 — re-exported for tests
    CheckResult,
    DEPTH_CHECK_MODES,
    SPOT_CHECK_PATTERNS,
    _check_review_depth,
    _check_skill_stamp,
    _check_stamps,
    _maybe_spot_check,
    _spot_check_files,
    detect_and_run_lint,
    detect_and_run_tests,
)
from finalize_common import EVAL_DIMENSION_WEIGHTS, fail  # noqa: E402,F401
from finalize_precommit import (  # noqa: E402,F401 — re-exported for tests
    _check_test_plans,
    _cleanup_test_plans,
    _compress_test_plans_section,
    _decide_precommit,
    _require_test_plan,
    finalize_precommit,
)
from finalize_render import (  # noqa: E402
    compose_assess_markdown,
    compose_evaluate_markdown,
    compose_reviewer_markdown,
)
from finalize_schema import (  # noqa: E402
    compute_evaluate_score,
    grade_letter,
    merge_dimension_scores,
    read_findings,
    validate_assess_findings,
    validate_evaluate_findings,
    validate_precommit_findings,
    validate_reviewer_findings,
)
from gate_hook import get_config_value, load_gate_config  # noqa: E402
from mechanical_scorer import score_codebase  # noqa: E402
from project_root import resolve_project_root  # noqa: E402

SUPPORTED_SKILLS = {"precommit", "evaluate", "reviewer", "assess"}

# Re-export private names for tests (tests/test_finalize_report.py)
_validate_precommit_findings = validate_precommit_findings
_validate_evaluate_findings = validate_evaluate_findings
_validate_reviewer_findings = validate_reviewer_findings
_validate_assess_findings = validate_assess_findings
_compute_evaluate_score = compute_evaluate_score
_grade_letter = grade_letter
_read_findings = read_findings
_fail = fail

COMPLETENESS_FLOOR_WHEN_GREEN = 90   # tests + lint pass → completeness at least this
COMPLETENESS_CAP_WHEN_TESTS_FAIL = 50


# --- Decisions ----------------------------------------------------------------


def _decide_evaluate(
    dimensions: dict, test: CheckResult, lint: CheckResult, threshold: int,
) -> tuple[bool, int, list[str]]:
    score = compute_evaluate_score(dimensions)
    reasons = checks.mechanical_reasons(test, lint)
    if score < threshold:
        reasons.append(f"score {score} below threshold {threshold}")
    return (len(reasons) == 0), score, reasons


def _decide_reviewer(findings: dict, test: CheckResult, lint: CheckResult) -> tuple[bool, list[str]]:
    reasons = checks.mechanical_reasons(test, lint)
    high = findings["findings"]["high"]
    if high > 0:
        reasons.append(f"high-severity findings: {high}")
    return (len(reasons) == 0), reasons


def _decide_assess(findings: dict, test: CheckResult, lint: CheckResult) -> tuple[bool, list[str]]:
    reasons = checks.mechanical_reasons(test, lint)
    fix_now = findings["findings"]["fix_now"]
    if fix_now > 0:
        reasons.append(f"critical fix_now findings: {fix_now}")
    return (len(reasons) == 0), reasons


# --- Gates --------------------------------------------------------------------


def _write_report_and_flag(
    project_dir: Path, skill: str, slug: str, markdown: str, passed: bool, score: int | None = None,
) -> tuple[Path, Path | None, str]:
    report_id = uuid.uuid4().hex[:8]
    out_path = checks._report_path(project_dir, skill, slug, report_id)
    out_path.write_text(markdown, encoding="utf-8")
    gate_flag = checks._write_gate_flag(project_dir, skill, score=score) if passed else None
    return out_path, gate_flag, report_id


def _response(
    project_dir: Path, skill: str, passed: bool, out_path: Path, gate_flag: Path | None,
    report_id: str, test: CheckResult, lint: CheckResult, reasons: list[str], **extra,
) -> int:
    payload = {"skill": skill, "passed": passed, **extra}
    payload.update({
        "report_path": str(out_path.relative_to(project_dir)),
        "report_id": report_id,
        "gate_flag": str(gate_flag.relative_to(project_dir)) if gate_flag else None,
        "mechanical": {"tests_passed": test.passed, "lint_passed": lint.passed},
        "blocking_reasons": reasons,
    })
    return checks._emit_response(payload, passed)


def finalize_evaluate(project_dir: Path, findings_path: Path) -> int:
    findings = validate_evaluate_findings(read_findings(findings_path))
    config = load_gate_config(project_dir)
    threshold = int(get_config_value(config, "eval_threshold", 95))

    # Mechanical scoring — the agent cannot raise these
    mechanical = score_codebase(project_dir)
    test, lint = checks._run_mechanical(project_dir, config)
    if test.passed and lint.passed:
        mechanical["completeness"] = max(mechanical["completeness"], COMPLETENESS_FLOOR_WHEN_GREEN)
    elif not test.passed:
        mechanical["completeness"] = min(mechanical["completeness"], COMPLETENESS_CAP_WHEN_TESTS_FAIL)

    # Agent findings can only lower a dimension (e.g. a forgeable stamp the
    # grep-based scorer cannot see); they can never raise one.
    agent_dimensions = findings.get("dimensions")
    dimensions = merge_dimension_scores(mechanical, agent_dimensions)
    findings["dimensions"] = dimensions

    passed, score, reasons = _decide_evaluate(dimensions, test, lint, threshold)
    report_id = uuid.uuid4().hex[:8]
    markdown = compose_evaluate_markdown(findings, test, lint, passed, score, threshold, reasons, report_id)
    out_path = checks._report_path(project_dir, "evaluate", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")
    gate_flag = checks._write_gate_flag(project_dir, "evaluate", score=score) if passed else None

    return _response(
        project_dir, "evaluate", passed, out_path, gate_flag, report_id, test, lint, reasons,
        score=score, threshold=threshold, dimensions=dimensions,
        mechanical_dimensions=mechanical, agent_dimensions=agent_dimensions,
    )


def finalize_reviewer(project_dir: Path, findings_path: Path) -> int:
    findings = validate_reviewer_findings(read_findings(findings_path))
    config = load_gate_config(project_dir)
    test, lint = checks._run_mechanical(project_dir, config)
    passed, reasons = _decide_reviewer(findings, test, lint)

    # Reviewer must have been invoked via the Skill tool (genuine stamp)
    stamp_issues = checks._check_skill_stamp(project_dir, "reviewer")
    reasons.extend(stamp_issues)

    # Review depth — safe/standard modes only
    from mode_resolver import resolve_mode_from_config
    current_mode = resolve_mode_from_config(config or {})
    reasons.extend(checks._check_review_depth(
        checks._get_session_action_audit(), current_mode.name, reviewer_stamp=not stamp_issues,
    ))
    passed = passed and not stamp_issues and len(reasons) == 0

    report_id = uuid.uuid4().hex[:8]
    markdown = compose_reviewer_markdown(findings, test, lint, passed, reasons, report_id)
    out_path = checks._report_path(project_dir, "reviewer", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")
    gate_flag = checks._write_gate_flag(project_dir, "reviewer") if passed else None
    return _response(project_dir, "reviewer", passed, out_path, gate_flag, report_id, test, lint, reasons)


def finalize_assess(project_dir: Path, findings_path: Path) -> int:
    findings = validate_assess_findings(read_findings(findings_path))
    config = load_gate_config(project_dir)
    test, lint = checks._run_mechanical(project_dir, config)
    passed, reasons = _decide_assess(findings, test, lint)

    report_id = uuid.uuid4().hex[:8]
    markdown = compose_assess_markdown(findings, test, lint, passed, reasons, report_id)
    out_path = checks._report_path(project_dir, "assess", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")
    gate_flag = checks._write_gate_flag(project_dir, "assess") if passed else None
    return _response(project_dir, "assess", passed, out_path, gate_flag, report_id, test, lint, reasons)


# --- CLI ----------------------------------------------------------------------


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        fail("usage: finalize_report.py <skill> <findings.json>")

    skill = argv[1]
    findings_path = Path(argv[2]).resolve()
    if skill not in SUPPORTED_SKILLS:
        fail(
            f"skill '{skill}' not yet supported by finalize_report.py. "
            f"Supported: {sorted(SUPPORTED_SKILLS)}"
        )

    project_dir = resolve_project_root(hint=findings_path)
    handlers = {
        "precommit": finalize_precommit,
        "evaluate": finalize_evaluate,
        "reviewer": finalize_reviewer,
        "assess": finalize_assess,
    }
    return handlers[skill](project_dir, findings_path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
