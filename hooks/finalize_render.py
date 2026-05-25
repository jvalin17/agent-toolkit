"""Markdown report composition for finalize_report."""

from __future__ import annotations

from datetime import datetime, timezone

from finalize_common import EVAL_DIMENSION_WEIGHTS, inline, trim_detail
from finalize_schema import grade_letter
from gate.attest import CheckResult


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _report_header(skill: str, title: str, slug: str, report_id: str, extra_rows: str = "") -> str:
    date = _utc_date()
    return f"""<!-- agent-toolkit:{skill} | v1 | {date} | {report_id} -->
<!-- writer: hooks/finalize_report.py — agent did not write this file -->
# {title}

| Field | Value |
|-------|-------|
| Status | completed |
| Writer | hooks/finalize_report.py |
| Skill | {skill} |
| Slug | {slug} |
| Date (UTC) | {date} |
{extra_rows}"""


def _append_summary_and_gate(md: str, summary: str, final_marker: str, pass_line: str = "") -> str:
    if summary:
        md += f"\n## Summary\n\n{summary}\n"
    if pass_line:
        md += f"\n{pass_line}\n"
    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md


def mechanical_table(test: CheckResult, lint: CheckResult) -> str:
    test_status = "passed" if test.passed else "FAILED"
    lint_status = "passed" if lint.passed else "FAILED"
    return f"""## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `{test.name}` | {test_status} | {trim_detail(test.detail)} |
| lint  | `{lint.name}` | {lint_status} | {trim_detail(lint.detail)} |
"""


def compose_precommit_markdown(
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
    ready: bool,
    reasons: list[str],
    report_id: str,
) -> str:
    slug = findings["slug"]
    instr = findings["instructions"]
    rules = findings["rules"]
    readme = findings["readme"]
    tm = findings["tests_meaningful"]
    appv = findings["app_verification"]
    summary = findings.get("summary", "").strip()

    final_marker = (
        "[x] READY TO COMMIT\n[ ] BLOCKED"
        if ready
        else f"[ ] READY TO COMMIT\n[x] BLOCKED — {'; '.join(reasons)}"
    )

    md = _report_header("precommit", f"Pre-commit Report: {slug}", slug, report_id)
    md += f"\n{mechanical_table(test, lint)}\n## Findings (agent-authored)\n\n"
    md += (
        f"- Instructions: {instr['addressed']}/{instr['total']} addressed\n"
        f"- Test quality: {tm['result']}{inline(' — ', tm.get('evidence'))}\n"
        f"- Rules: {rules['violations']} violation(s)\n"
        f"- README: {'PASS' if readme['passed'] else 'FAIL'}{inline(' — ', readme.get('details'))}\n"
        f"- App verification: {appv['status']}{inline(' — ', appv.get('notes'))}\n"
    )
    return _append_summary_and_gate(md, summary, final_marker)


def compose_evaluate_markdown(
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
    grade = grade_letter(score)
    summary = findings.get("summary", "").strip()

    dim_rows = [
        f"| {key.replace('_', ' ').title()} | {dims[key]}% | {int(weight * 100)}% | {round(dims[key] * weight)} |"
        for key, weight in EVAL_DIMENSION_WEIGHTS.items()
    ]

    final_marker = (
        f"[x] PASSED — score {score}% ≥ threshold {threshold}%\n[ ] BLOCKED"
        if passed
        else f"[ ] PASSED\n[x] BLOCKED — {'; '.join(reasons)}"
    )

    extra = f"| Threshold | {threshold}% |\n"
    md = _report_header("evaluate", f"Evaluation: {topic}\n# Score: **{score}%** ({grade})", slug, report_id, extra)
    md += f"\n| Dimension | Score | Weight | Weighted |\n|-----------|-------|--------|----------|\n"
    md += "\n".join(dim_rows)
    md += f"\n| **Overall** | | | **{score}%** |\n\n{mechanical_table(test, lint)}\n"
    return _append_summary_and_gate(md, summary, final_marker)


def compose_reviewer_markdown(
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
    summary = findings.get("summary", "").strip()
    areas_line = ", ".join(findings.get("areas_reviewed") or []) or "—"

    if passed:
        final_marker = "[x] PASSED\n[ ] BLOCKED"
        pass_line = "PASSED — no high-severity findings remain."
    else:
        final_marker = f"[ ] PASSED\n[x] BLOCKED — {'; '.join(reasons)}"
        pass_line = ""

    extra = f"| Areas reviewed | {areas_line} |\n"
    md = _report_header("reviewer", f"Reviewer Report: {topic}", slug, report_id, extra)
    md += (
        f"\n## Findings Summary\n\n| Severity | Count |\n|----------|-------|\n"
        f"| High | {counts['high']} |\n| Medium | {counts['medium']} |\n| Low | {counts['low']} |\n\n"
        f"{mechanical_table(test, lint)}\n"
    )
    return _append_summary_and_gate(md, summary, final_marker, pass_line)


def compose_assess_markdown(
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
    summary = findings.get("summary", "").strip()

    if passed:
        final_marker = "[x] PASSED\n[ ] BLOCKED"
        pass_line = "PASSED — no critical anti-patterns remain."
        fix_now_section = "### [!!] Fix Now\n\nNone.\n"
    else:
        final_marker = f"[ ] PASSED\n[x] BLOCKED — {'; '.join(reasons)}"
        pass_line = ""
        fix_now_section = f"### [!!] Fix Now\n\n{counts['fix_now']} critical finding(s) remain.\n"

    md = _report_header("assess", f"Assess Report: {topic}", slug, report_id)
    md += (
        f"\n## Findings Summary\n\n| Bucket | Count |\n|--------|-------|\n"
        f"| [!!] Fix now | {counts['fix_now']} |\n| [~] Consider | {counts['consider']} |\n"
        f"| [ok] Good as-is | {counts['good']} |\n\n{fix_now_section}{mechanical_table(test, lint)}\n"
    )
    return _append_summary_and_gate(md, summary, final_marker, pass_line)
