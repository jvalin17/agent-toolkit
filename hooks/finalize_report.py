#!/usr/bin/env python3
"""finalize_report.py — Hook-owned writer for skill reports.

The toolkit's report-protection model (G-REPORT-1) blocks agents from
writing into reports/. This hook is the ONLY allowed writer: it accepts
an agent-produced findings.json, re-runs the mechanical claims itself
(so the agent cannot fabricate command results), and composes a canonical
report file in reports/<skill>/.

Usage:
    python3 hooks/finalize_report.py <skill> <findings_json_path>

Currently supports:
    - precommit
    - evaluate
    - reviewer
    - assess

Exit codes:
    0 — report written, gate-ready
    1 — report written, BLOCKED (mechanical or finding failures)
    2 — validation error (bad findings.json, unknown skill)
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Make sibling hooks importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_hook import get_config_value, load_gate_config
from project_root import resolve_project_root

# Reach the toolkit's gate/ package (project root on sys.path)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gate.attest import (  # noqa: E402  — must come after sys.path tweak
    CheckResult,
    detect_and_run_lint,
    detect_and_run_tests,
)


SUPPORTED_SKILLS = {"precommit", "evaluate", "reviewer", "assess"}

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

EVAL_DIMENSION_WEIGHTS: dict[str, float] = {
    "completeness": 0.30,
    "code_quality": 0.25,
    "security": 0.20,
    "test_quality": 0.15,
    "efficiency": 0.10,
}


# --- I/O helpers ----------------------------------------------------------


def _fail(msg: str, code: int = 2) -> "NoReturn":  # type: ignore[name-defined]
    sys.stderr.write(f"finalize_report: {msg}\n")
    sys.exit(code)


def _read_findings(path: Path) -> dict:
    if not path.is_file():
        _fail(f"findings file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"findings is not valid JSON: {exc}")
    if not isinstance(data, dict):
        _fail("findings root must be a JSON object")
    return data


# --- Schema validation ----------------------------------------------------


def _require(d: dict, key: str, kind, context: str) -> object:
    if key not in d:
        _fail(f"{context}: missing required key '{key}'")
    value = d[key]
    if not isinstance(value, kind):
        _fail(
            f"{context}: key '{key}' must be {kind.__name__}, "
            f"got {type(value).__name__}"
        )
    return value


def _validate_slug(data: dict, skill_name: str) -> None:
    skill = _require(data, "skill", str, "findings")
    if skill != skill_name:
        _fail(f"findings.skill must be '{skill_name}', got '{skill}'")

    slug = _require(data, "slug", str, "findings")
    if not SLUG_RE.match(slug):
        _fail(
            f"findings.slug '{slug}' is not a valid slug "
            "(lowercase, alphanumeric, dashes, 1-64 chars)"
        )


def _require_nonneg_int(d: dict, key: str, context: str) -> int:
    val = _require(d, key, int, context)
    if val < 0:
        _fail(f"{context}: '{key}' must be >= 0 (got {val})")
    return val


def _validate_precommit_findings(data: dict) -> dict:
    """Minimal but enforced schema for precommit findings.

    Schema (all keys required unless marked optional):
        skill (str)        — must equal "precommit"
        slug  (str)        — short kebab-case identifier (also used in filename)
        instructions (obj) — { addressed: int, total: int, items?: list }
        rules        (obj) — { violations: int, items?: list }
        readme       (obj) — { passed: bool, details?: str }
        tests_meaningful (obj) — { result: "verified"|"sloppy"|"skipped",
                                   evidence?: str }
        app_verification (obj) — { status: "done"|"pending"|"na",
                                   notes?: str }
        summary (str, optional) — agent narrative

    The hook ALSO re-runs the mechanical test/lint commands; the agent
    does not get to claim those.
    """
    skill = _require(data, "skill", str, "findings")
    if skill != "precommit":
        _fail(f"findings.skill must be 'precommit', got '{skill}'")

    slug = _require(data, "slug", str, "findings")
    if not SLUG_RE.match(slug):
        _fail(
            f"findings.slug '{slug}' is not a valid slug "
            "(lowercase, alphanumeric, dashes, 1-64 chars)"
        )

    instr = _require(data, "instructions", dict, "findings")
    addressed = _require(instr, "addressed", int, "findings.instructions")
    total = _require(instr, "total", int, "findings.instructions")
    if addressed < 0 or total < 0 or addressed > total:
        _fail(
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
        _fail(
            "findings.tests_meaningful.result must be one of "
            f"verified|sloppy|skipped (got '{tm_result}')"
        )

    appv = _require(data, "app_verification", dict, "findings")
    appv_status = _require(appv, "status", str, "findings.app_verification")
    if appv_status not in ("done", "pending", "na"):
        _fail(
            "findings.app_verification.status must be done|pending|na "
            f"(got '{appv_status}')"
        )

    return data


def _validate_evaluate_findings(data: dict) -> dict:
    """Minimal but enforced schema for evaluate findings.

    Schema (all keys required unless marked optional):
        skill (str)       — must equal "evaluate"
        slug  (str)       — short kebab-case identifier
        topic (str)       — what was evaluated
        dimensions (obj)  — completeness, code_quality, security,
                            test_quality, efficiency (each int 0-100)
        summary (str, optional) — agent narrative

    The hook recomputes the overall score from dimension weights; the agent
    cannot claim a higher score than the dimensions support. Mechanical
    test/lint are also re-run.
    """
    skill = _require(data, "skill", str, "findings")
    if skill != "evaluate":
        _fail(f"findings.skill must be 'evaluate', got '{skill}'")

    slug = _require(data, "slug", str, "findings")
    if not SLUG_RE.match(slug):
        _fail(
            f"findings.slug '{slug}' is not a valid slug "
            "(lowercase, alphanumeric, dashes, 1-64 chars)"
        )

    _require(data, "topic", str, "findings")
    dims = _require(data, "dimensions", dict, "findings")

    for key in EVAL_DIMENSION_WEIGHTS:
        if key not in dims:
            _fail(f"findings.dimensions: missing required key '{key}'")
        score = dims[key]
        if not isinstance(score, int):
            _fail(
                f"findings.dimensions.{key} must be int, "
                f"got {type(score).__name__}"
            )
        if score < 0 or score > 100:
            _fail(
                f"findings.dimensions.{key} must be 0..100 (got {score})"
            )

    return data


def _validate_reviewer_findings(data: dict) -> dict:
    """Schema for reviewer findings.

    Required:
        skill, slug, topic, findings { high, medium, low } (non-negative ints)
    Optional:
        areas_reviewed (list of str), summary (str)
    """
    _validate_slug(data, "reviewer")
    _require(data, "topic", str, "findings")
    counts = _require(data, "findings", dict, "findings")
    for key in ("high", "medium", "low"):
        _require_nonneg_int(counts, key, f"findings.{key}")

    areas = data.get("areas_reviewed", [])
    if areas is not None and not isinstance(areas, list):
        _fail("findings.areas_reviewed must be a list if present")
    if isinstance(areas, list):
        for item in areas:
            if not isinstance(item, str):
                _fail("findings.areas_reviewed items must be strings")

    return data


def _validate_assess_findings(data: dict) -> dict:
    """Schema for assess findings.

    Required:
        skill, slug, topic, findings { fix_now, consider, good } (non-negative ints)
    Optional:
        summary (str)
    """
    _validate_slug(data, "assess")
    _require(data, "topic", str, "findings")
    counts = _require(data, "findings", dict, "findings")
    for key in ("fix_now", "consider", "good"):
        _require_nonneg_int(counts, key, f"findings.{key}")

    return data


def _compute_evaluate_score(dimensions: dict) -> int:
    total = sum(dimensions[k] * w for k, w in EVAL_DIMENSION_WEIGHTS.items())
    return round(total)


def _grade_letter(score: int) -> str:
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


# --- Mechanical re-run ----------------------------------------------------


def _run_mechanical(project_dir: Path, config: dict) -> tuple[CheckResult, CheckResult]:
    test = detect_and_run_tests(project_dir, config)
    lint = detect_and_run_lint(project_dir, config)
    return test, lint


# --- Gate decision --------------------------------------------------------


def _decide_precommit(
    findings: dict, test: CheckResult, lint: CheckResult
) -> tuple[bool, list[str]]:
    """Return (ready, blocking_reasons).

    Mechanical truth wins: any failed re-run blocks the gate regardless
    of what the agent claims. Findings violations also block.
    """
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
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
    threshold: int,
) -> tuple[bool, int, list[str]]:
    """Return (passed, score, blocking_reasons)."""
    reasons: list[str] = []
    score = _compute_evaluate_score(findings["dimensions"])

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


# --- Report composition ---------------------------------------------------


def _compose_precommit_markdown(
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
    ready: bool,
    reasons: list[str],
    report_id: str,
) -> str:
    slug = findings["slug"]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    instr = findings["instructions"]
    rules = findings["rules"]
    readme = findings["readme"]
    tm = findings["tests_meaningful"]
    appv = findings["app_verification"]
    summary = findings.get("summary", "").strip()

    test_status = "passed" if test.passed else "FAILED"
    lint_status = "passed" if lint.passed else "FAILED"

    final_marker = (
        "[x] READY TO COMMIT\n[ ] BLOCKED"
        if ready
        else f"[ ] READY TO COMMIT\n[x] BLOCKED — {'; '.join(reasons)}"
    )

    test_detail = _trim_detail(test.detail)
    lint_detail = _trim_detail(lint.detail)

    md = f"""<!-- agent-toolkit:precommit | v1 | {date} | {report_id} -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Pre-commit Report: {slug}

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | precommit |
| Slug | {slug} |
| Date (UTC) | {date} |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `{test.name}` | {test_status} | {test_detail} |
| lint  | `{lint.name}` | {lint_status} | {lint_detail} |

## Findings (agent-authored)

- Instructions: {instr['addressed']}/{instr['total']} addressed
- Test quality: {tm['result']}{_inline(' — ', tm.get('evidence'))}
- Rules: {rules['violations']} violation(s)
- README: {'PASS' if readme['passed'] else 'FAIL'}{_inline(' — ', readme.get('details'))}
- App verification: {appv['status']}{_inline(' — ', appv.get('notes'))}
"""

    if summary:
        md += f"\n## Summary\n\n{summary}\n"

    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md


def _compose_evaluate_markdown(
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
    passed: bool,
    score: int,
    threshold: int,
    reasons: list[str],
    report_id: str,
) -> str:
    slug = findings["slug"]
    topic = findings["topic"]
    dims = findings["dimensions"]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    grade = _grade_letter(score)
    summary = findings.get("summary", "").strip()

    test_status = "passed" if test.passed else "FAILED"
    lint_status = "passed" if lint.passed else "FAILED"
    test_detail = _trim_detail(test.detail)
    lint_detail = _trim_detail(lint.detail)

    dim_rows = []
    for key, weight in EVAL_DIMENSION_WEIGHTS.items():
        label = key.replace("_", " ").title()
        dim_score = dims[key]
        weighted = round(dim_score * weight)
        dim_rows.append(
            f"| {label} | {dim_score}% | {int(weight * 100)}% | {weighted} |"
        )
    dim_table = "\n".join(dim_rows)

    if passed:
        final_marker = (
            f"[x] PASSED — score {score}% ≥ threshold {threshold}%\n"
            f"[ ] BLOCKED"
        )
    else:
        final_marker = (
            f"[ ] PASSED\n"
            f"[x] BLOCKED — {'; '.join(reasons)}"
        )

    md = f"""<!-- agent-toolkit:evaluate | v1 | {date} | {report_id} -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Evaluation: {topic}
# Score: **{score}%** ({grade})

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | evaluate |
| Slug | {slug} |
| Threshold | {threshold}% |
| Date (UTC) | {date} |

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
{dim_table}
| **Overall** | | | **{score}%** |

## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `{test.name}` | {test_status} | {test_detail} |
| lint  | `{lint.name}` | {lint_status} | {lint_detail} |
"""

    if summary:
        md += f"\n## Summary\n\n{summary}\n"

    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md


def _mechanical_table(test: CheckResult, lint: CheckResult) -> str:
    test_status = "passed" if test.passed else "FAILED"
    lint_status = "passed" if lint.passed else "FAILED"
    test_detail = _trim_detail(test.detail)
    lint_detail = _trim_detail(lint.detail)
    return f"""## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `{test.name}` | {test_status} | {test_detail} |
| lint  | `{lint.name}` | {lint_status} | {lint_detail} |
"""


def _compose_reviewer_markdown(
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
    passed: bool,
    reasons: list[str],
    report_id: str,
) -> str:
    slug = findings["slug"]
    topic = findings["topic"]
    counts = findings["findings"]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    summary = findings.get("summary", "").strip()
    areas = findings.get("areas_reviewed") or []

    if passed:
        final_marker = "[x] PASSED\n[ ] BLOCKED"
        pass_line = "PASSED — no high-severity findings remain."
    else:
        final_marker = f"[ ] PASSED\n[x] BLOCKED — {'; '.join(reasons)}"
        pass_line = ""

    areas_line = ", ".join(areas) if areas else "—"

    md = f"""<!-- agent-toolkit:reviewer | v1 | {date} | {report_id} -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Reviewer Report: {topic}

| Field | Value |
|-------|-------|
| **Status** | completed |
| Writer | hooks/finalize_report.py |
| Skill | reviewer |
| Slug | {slug} |
| Areas reviewed | {areas_line} |
| Date (UTC) | {date} |

## Findings Summary

| Severity | Count |
|----------|-------|
| High | {counts['high']} |
| Medium | {counts['medium']} |
| Low | {counts['low']} |

{_mechanical_table(test, lint)}
"""

    if summary:
        md += f"\n## Summary\n\n{summary}\n"

    if pass_line:
        md += f"\n{pass_line}\n"

    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md


def _compose_assess_markdown(
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
    passed: bool,
    reasons: list[str],
    report_id: str,
) -> str:
    slug = findings["slug"]
    topic = findings["topic"]
    counts = findings["findings"]
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    summary = findings.get("summary", "").strip()

    if passed:
        final_marker = "[x] PASSED\n[ ] BLOCKED"
        pass_line = "PASSED — no critical anti-patterns remain."
        fix_now_section = "### [!!] Fix Now\n\nNone.\n"
    else:
        final_marker = f"[ ] PASSED\n[x] BLOCKED — {'; '.join(reasons)}"
        pass_line = ""
        fix_now_section = (
            f"### [!!] Fix Now\n\n{counts['fix_now']} critical finding(s) remain.\n"
        )

    md = f"""<!-- agent-toolkit:assess | v1 | {date} | {report_id} -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# Assess Report: {topic}

| Field | Value |
|-------|-------|
| **Status** | completed |
| Writer | hooks/finalize_report.py |
| Skill | assess |
| Slug | {slug} |
| Date (UTC) | {date} |

## Findings Summary

| Bucket | Count |
|--------|-------|
| [!!] Fix now | {counts['fix_now']} |
| [~] Consider | {counts['consider']} |
| [ok] Good as-is | {counts['good']} |

{fix_now_section}
{_mechanical_table(test, lint)}
"""

    if summary:
        md += f"\n## Summary\n\n{summary}\n"

    if pass_line:
        md += f"\n{pass_line}\n"

    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md


def _trim_detail(detail: str, limit: int = 200) -> str:
    if not detail:
        return "—"
    s = detail.replace("\n", " ").replace("|", "\\|").strip()
    if len(s) > limit:
        s = s[: limit - 1] + "…"
    return s


def _inline(prefix: str, value) -> str:
    if not value:
        return ""
    return f"{prefix}{str(value).strip()}"


# --- Filesystem write -----------------------------------------------------


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


def _write_precommit_gate(project_dir: Path) -> Path:
    """Write legacy precommit gate flag (G-GATE-1: hooks only when gate_protect is on)."""
    gates_dir = project_dir / ".gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    flag = gates_dir / "precommit-passed"
    flag.write_text(f"READY {date}\n", encoding="utf-8")
    return flag


def _write_evaluate_gate(project_dir: Path, score: int) -> Path:
    """Write legacy evaluate gate flag (G-GATE-1: hooks only when gate_protect is on)."""
    gates_dir = project_dir / ".gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    flag = gates_dir / "evaluate-passed"
    flag.write_text(f"PASSED {score}% evaluate {date}\n", encoding="utf-8")
    return flag


def _write_reviewer_gate(project_dir: Path) -> Path:
    """Write legacy reviewer gate flag (G-GATE-1: hooks only when gate_protect is on)."""
    gates_dir = project_dir / ".gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    flag = gates_dir / "reviewer-passed"
    flag.write_text(f"PASSED reviewer {date}\n", encoding="utf-8")
    return flag


def _write_assess_gate(project_dir: Path) -> Path:
    """Write legacy assess gate flag (G-GATE-1: hooks only when gate_protect is on)."""
    gates_dir = project_dir / ".gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    flag = gates_dir / "assess-passed"
    flag.write_text(f"PASSED assess {date}\n", encoding="utf-8")
    return flag


def finalize_precommit(project_dir: Path, findings_path: Path) -> int:
    findings = _validate_precommit_findings(_read_findings(findings_path))
    config = load_gate_config(project_dir)

    test, lint = _run_mechanical(project_dir, config)
    ready, reasons = _decide_precommit(findings, test, lint)
    report_id = uuid.uuid4().hex[:8]
    markdown = _compose_precommit_markdown(
        findings, test, lint, ready, reasons, report_id
    )

    out_path = _report_path(project_dir, "precommit", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")

    gate_flag = None
    if ready:
        gate_flag = _write_precommit_gate(project_dir)

    response = {
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
    }
    sys.stdout.write(json.dumps(response, indent=2) + "\n")
    return 0 if ready else 1


def finalize_evaluate(project_dir: Path, findings_path: Path) -> int:
    findings = _validate_evaluate_findings(_read_findings(findings_path))
    config = load_gate_config(project_dir)
    threshold = int(get_config_value(config, "eval_threshold", 95))

    test, lint = _run_mechanical(project_dir, config)
    passed, score, reasons = _decide_evaluate(findings, test, lint, threshold)
    report_id = uuid.uuid4().hex[:8]
    markdown = _compose_evaluate_markdown(
        findings, test, lint, passed, score, threshold, reasons, report_id
    )

    out_path = _report_path(project_dir, "evaluate", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")

    gate_flag = None
    if passed:
        gate_flag = _write_evaluate_gate(project_dir, score)

    response = {
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
    }
    sys.stdout.write(json.dumps(response, indent=2) + "\n")
    return 0 if passed else 1


def finalize_reviewer(project_dir: Path, findings_path: Path) -> int:
    findings = _validate_reviewer_findings(_read_findings(findings_path))
    config = load_gate_config(project_dir)

    test, lint = _run_mechanical(project_dir, config)
    passed, reasons = _decide_reviewer(findings, test, lint)
    report_id = uuid.uuid4().hex[:8]
    markdown = _compose_reviewer_markdown(
        findings, test, lint, passed, reasons, report_id
    )

    out_path = _report_path(project_dir, "reviewer", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")

    gate_flag = None
    if passed:
        gate_flag = _write_reviewer_gate(project_dir)

    response = {
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
    }
    sys.stdout.write(json.dumps(response, indent=2) + "\n")
    return 0 if passed else 1


def finalize_assess(project_dir: Path, findings_path: Path) -> int:
    findings = _validate_assess_findings(_read_findings(findings_path))
    config = load_gate_config(project_dir)

    test, lint = _run_mechanical(project_dir, config)
    passed, reasons = _decide_assess(findings, test, lint)
    report_id = uuid.uuid4().hex[:8]
    markdown = _compose_assess_markdown(
        findings, test, lint, passed, reasons, report_id
    )

    out_path = _report_path(project_dir, "assess", findings["slug"], report_id)
    out_path.write_text(markdown, encoding="utf-8")

    gate_flag = None
    if passed:
        gate_flag = _write_assess_gate(project_dir)

    response = {
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
    }
    sys.stdout.write(json.dumps(response, indent=2) + "\n")
    return 0 if passed else 1


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        _fail("usage: finalize_report.py <skill> <findings.json>")

    skill = argv[1]
    findings_path = Path(argv[2]).resolve()

    if skill not in SUPPORTED_SKILLS:
        _fail(
            f"skill '{skill}' not yet supported by finalize_report.py. "
            f"Supported: {sorted(SUPPORTED_SKILLS)}"
        )

    project_dir = resolve_project_root(hint=findings_path)
    if skill == "precommit":
        return finalize_precommit(project_dir, findings_path)
    if skill == "evaluate":
        return finalize_evaluate(project_dir, findings_path)
    if skill == "reviewer":
        return finalize_reviewer(project_dir, findings_path)
    if skill == "assess":
        return finalize_assess(project_dir, findings_path)
    _fail(f"no handler wired for skill '{skill}'")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
