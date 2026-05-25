"""Markdown report composition for finalize_report."""

from __future__ import annotations

from datetime import datetime, timezone

from finalize_common import EVAL_DIMENSION_WEIGHTS, inline, trim_detail
from finalize_schema import grade_letter
from gate.attest import CheckResult


def mechanical_table(test: CheckResult, lint: CheckResult) -> str:
    test_status = "passed" if test.passed else "FAILED"
    lint_status = "passed" if lint.passed else "FAILED"
    test_detail = trim_detail(test.detail)
    lint_detail = trim_detail(lint.detail)
    return f"""## Mechanical Re-run (hook-owned)

| Check | Command | Result | Detail |
|-------|---------|--------|--------|
| tests | `{test.name}` | {test_status} | {test_detail} |
| lint  | `{lint.name}` | {lint_status} | {lint_detail} |
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
| tests | `{test.name}` | {test_status} | {trim_detail(test.detail)} |
| lint  | `{lint.name}` | {lint_status} | {trim_detail(lint.detail)} |

## Findings (agent-authored)

- Instructions: {instr['addressed']}/{instr['total']} addressed
- Test quality: {tm['result']}{inline(' — ', tm.get('evidence'))}
- Rules: {rules['violations']} violation(s)
- README: {'PASS' if readme['passed'] else 'FAIL'}{inline(' — ', readme.get('details'))}
- App verification: {appv['status']}{inline(' — ', appv.get('notes'))}
"""

    if summary:
        md += f"\n## Summary\n\n{summary}\n"

    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md


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
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    grade = grade_letter(score)
    summary = findings.get("summary", "").strip()

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
        final_marker = f"[ ] PASSED\n[x] BLOCKED — {'; '.join(reasons)}"

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

{mechanical_table(test, lint)}
"""

    if summary:
        md += f"\n## Summary\n\n{summary}\n"

    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md


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

{mechanical_table(test, lint)}
"""

    if summary:
        md += f"\n## Summary\n\n{summary}\n"

    if pass_line:
        md += f"\n{pass_line}\n"

    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md


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
{mechanical_table(test, lint)}
"""

    if summary:
        md += f"\n## Summary\n\n{summary}\n"

    if pass_line:
        md += f"\n{pass_line}\n"

    md += f"\n## Final Gate\n\n{final_marker}\n"
    return md
