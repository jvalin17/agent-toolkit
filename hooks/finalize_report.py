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
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_hook import get_config_value, load_gate_config  # noqa: E402
from project_root import resolve_project_root  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gate.attest import (  # noqa: E402
    CheckResult,
    detect_and_run_lint,
    detect_and_run_tests,
)
from finalize_common import EVAL_DIMENSION_WEIGHTS, fail  # noqa: E402
from finalize_render import (  # noqa: E402
    compose_assess_markdown,
    compose_evaluate_markdown,
    compose_precommit_markdown,
    compose_reviewer_markdown,
)
from finalize_schema import (  # noqa: E402
    compute_evaluate_score,
    grade_letter,
    read_findings,
    validate_assess_findings,
    validate_evaluate_findings,
    validate_precommit_findings,
    validate_reviewer_findings,
)
from mechanical_scorer import score_codebase  # noqa: E402

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


def _run_mechanical(project_dir: Path, config: dict) -> tuple[CheckResult, CheckResult]:
    test = detect_and_run_tests(project_dir, config)
    lint = detect_and_run_lint(project_dir, config)
    return test, lint


def _decide_precommit(
    findings: dict, test: CheckResult, lint: CheckResult
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if not test.passed:
        reasons.append(f"test re-run failed: {test.name}")
    if not lint.passed:
        reasons.append(f"lint re-run failed: {lint.name}")

    instr = findings["instructions"]
    if instr["addressed"] < instr["total"]:
        reasons.append(
            f"instructions: {instr['addressed']}/{instr['total']} addressed"
        )

    if findings["rules"]["violations"] > 0:
        reasons.append(
            f"rules: {findings['rules']['violations']} violation(s)"
        )

    if not findings["readme"]["passed"]:
        reasons.append("readme: validation failed")

    if findings["tests_meaningful"]["result"] == "sloppy":
        reasons.append("test quality: sloppy tests detected")

    if findings["app_verification"]["status"] == "pending":
        reasons.append("app verification: still pending")

    return (len(reasons) == 0), reasons


def _decide_evaluate(
    dimensions: dict,
    test: CheckResult,
    lint: CheckResult,
    threshold: int,
) -> tuple[bool, int, list[str]]:
    reasons: list[str] = []
    score = compute_evaluate_score(dimensions)

    if not test.passed:
        reasons.append(f"test re-run failed: {test.name}")
    if not lint.passed:
        reasons.append(f"lint re-run failed: {lint.name}")
    if score < threshold:
        reasons.append(f"score {score} below threshold {threshold}")

    return (len(reasons) == 0), score, reasons


def _decide_reviewer(
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if not test.passed:
        reasons.append(f"test re-run failed: {test.name}")
    if not lint.passed:
        reasons.append(f"lint re-run failed: {lint.name}")

    high = findings["findings"]["high"]
    if high > 0:
        reasons.append(f"high-severity findings: {high}")

    return (len(reasons) == 0), reasons


def _decide_assess(
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if not test.passed:
        reasons.append(f"test re-run failed: {test.name}")
    if not lint.passed:
        reasons.append(f"lint re-run failed: {lint.name}")

    fix_now = findings["findings"]["fix_now"]
    if fix_now > 0:
        reasons.append(f"critical fix_now findings: {fix_now}")

    return (len(reasons) == 0), reasons


def _report_path(project_dir: Path, skill: str, slug: str, report_id: str) -> Path:
    target_dir = project_dir / "reports" / skill
    target_dir.mkdir(parents=True, exist_ok=True)
    fname_prefix = {
        "precommit": "pc",
        "evaluate": "eval",
        "reviewer": "review",
        "assess": "assess",
    }[skill]
    return target_dir / f"{fname_prefix}_{slug}_{report_id}.md"


def _write_gate_flag(project_dir: Path, skill: str, *, score: int | None = None) -> Path:
    gates_dir = project_dir / ".gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    flag = gates_dir / f"{skill}-passed"
    if skill == "precommit":
        flag.write_text(f"READY {date}\n", encoding="utf-8")
    elif skill == "evaluate":
        flag.write_text(f"PASSED {score}% evaluate {date}\n", encoding="utf-8")
    elif skill == "reviewer":
        flag.write_text(f"PASSED reviewer {date}\n", encoding="utf-8")
    else:
        flag.write_text(f"PASSED assess {date}\n", encoding="utf-8")
    return flag


def _emit_response(payload: dict, ok: bool) -> int:
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if ok else 1


def finalize_precommit(project_dir: Path, findings_path: Path) -> int:
    findings = validate_precommit_findings(read_findings(findings_path))
    config = load_gate_config(project_dir)

    test, lint = _run_mechanical(project_dir, config)
    ready, reasons = _decide_precommit(findings, test, lint)
    report_id = uuid.uuid4().hex[:8]
    markdown = compose_precommit_markdown(
        findings, test, lint, ready, reasons, report_id
    )

    out_path = _report_path(project_dir, "precommit", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")

    gate_flag = _write_gate_flag(project_dir, "precommit") if ready else None

    return _emit_response(
        {
            "skill": "precommit",
            "ready_to_commit": ready,
            "report_path": str(out_path.relative_to(project_dir)),
            "report_id": report_id,
            "gate_flag": str(gate_flag.relative_to(project_dir)) if gate_flag else None,
            "mechanical": {
                "tests_passed": test.passed,
                "lint_passed": lint.passed,
            },
            "blocking_reasons": reasons,
        },
        ready,
    )


def finalize_evaluate(project_dir: Path, findings_path: Path) -> int:
    findings = validate_evaluate_findings(read_findings(findings_path))
    config = load_gate_config(project_dir)
    threshold = int(get_config_value(config, "eval_threshold", 95))

    # Mechanical scoring — agent cannot influence these
    dimensions = score_codebase(project_dir)
    findings["dimensions"] = dimensions

    test, lint = _run_mechanical(project_dir, config)

    # Adjust completeness based on mechanical test/lint results
    if test.passed and lint.passed:
        dimensions["completeness"] = max(dimensions["completeness"], 90)
    elif not test.passed:
        dimensions["completeness"] = min(dimensions["completeness"], 50)

    passed, score, reasons = _decide_evaluate(dimensions, test, lint, threshold)
    report_id = uuid.uuid4().hex[:8]
    markdown = compose_evaluate_markdown(
        findings, test, lint, passed, score, threshold, reasons, report_id
    )

    out_path = _report_path(project_dir, "evaluate", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")

    gate_flag = (
        _write_gate_flag(project_dir, "evaluate", score=score) if passed else None
    )

    return _emit_response(
        {
            "skill": "evaluate",
            "passed": passed,
            "score": score,
            "threshold": threshold,
            "report_path": str(out_path.relative_to(project_dir)),
            "report_id": report_id,
            "gate_flag": str(gate_flag.relative_to(project_dir)) if gate_flag else None,
            "mechanical": {
                "tests_passed": test.passed,
                "lint_passed": lint.passed,
            },
            "blocking_reasons": reasons,
        },
        passed,
    )


def finalize_reviewer(project_dir: Path, findings_path: Path) -> int:
    findings = validate_reviewer_findings(read_findings(findings_path))
    config = load_gate_config(project_dir)

    test, lint = _run_mechanical(project_dir, config)
    passed, reasons = _decide_reviewer(findings, test, lint)
    report_id = uuid.uuid4().hex[:8]
    markdown = compose_reviewer_markdown(
        findings, test, lint, passed, reasons, report_id
    )

    out_path = _report_path(project_dir, "reviewer", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")

    gate_flag = _write_gate_flag(project_dir, "reviewer") if passed else None

    return _emit_response(
        {
            "skill": "reviewer",
            "passed": passed,
            "report_path": str(out_path.relative_to(project_dir)),
            "report_id": report_id,
            "gate_flag": str(gate_flag.relative_to(project_dir)) if gate_flag else None,
            "mechanical": {
                "tests_passed": test.passed,
                "lint_passed": lint.passed,
            },
            "blocking_reasons": reasons,
        },
        passed,
    )


def finalize_assess(project_dir: Path, findings_path: Path) -> int:
    findings = validate_assess_findings(read_findings(findings_path))
    config = load_gate_config(project_dir)

    test, lint = _run_mechanical(project_dir, config)
    passed, reasons = _decide_assess(findings, test, lint)
    report_id = uuid.uuid4().hex[:8]
    markdown = compose_assess_markdown(
        findings, test, lint, passed, reasons, report_id
    )

    out_path = _report_path(project_dir, "assess", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")

    gate_flag = _write_gate_flag(project_dir, "assess") if passed else None

    return _emit_response(
        {
            "skill": "assess",
            "passed": passed,
            "report_path": str(out_path.relative_to(project_dir)),
            "report_id": report_id,
            "gate_flag": str(gate_flag.relative_to(project_dir)) if gate_flag else None,
            "mechanical": {
                "tests_passed": test.passed,
                "lint_passed": lint.passed,
            },
            "blocking_reasons": reasons,
        },
        passed,
    )


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
