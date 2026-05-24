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

# Reach the toolkit's gate/ package (project root on sys.path)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gate.attest import (  # noqa: E402  — must come after sys.path tweak
    CheckResult,
    detect_and_run_lint,
    detect_and_run_tests,
)


SUPPORTED_SKILLS = {"precommit"}

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


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
    fname_prefix = {"precommit": "pc"}[skill]
    return target_dir / f"{fname_prefix}_{slug}_{report_id}.md"


# --- Entry point ----------------------------------------------------------


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

    response = {
        "skill": "precommit",
        "ready_to_commit": ready,
        "report_path": str(out_path.relative_to(project_dir)),
        "report_id": report_id,
        "mechanical": {
            "tests_passed": test.passed,
            "lint_passed": lint.passed,
        },
        "blocking_reasons": reasons,
    }
    sys.stdout.write(json.dumps(response, indent=2) + "\n")
    return 0 if ready else 1


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

    project_dir = Path.cwd()
    if skill == "precommit":
        return finalize_precommit(project_dir, findings_path)
    _fail(f"no handler wired for skill '{skill}'")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
