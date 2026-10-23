"""Precommit gate — decision logic, test-plan policy, and report writing.

Entry point is ``finalize_precommit``; ``finalize_report.py`` dispatches to it.
Shared checks (stamps, depth, spot checks, mechanical re-run) live in
``finalize_checks`` and are called through the module so tests can patch them
in one place.
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import finalize_checks as checks  # noqa: E402
from compliance import (  # noqa: E402
    check_diff_for_noqa_in_tests,
    check_diff_for_tautological_tests,
    check_diff_for_ui_without_e2e,
    check_diff_for_untested_functions,
    check_execution_plan_compliance,
    check_test_plan_coverage,
    format_test_plan_summary,
    generate_session_summary,
    validate_execution_plan,
    validate_test_plan,
)
from finalize_render import compose_precommit_markdown  # noqa: E402
from finalize_schema import read_findings, validate_precommit_findings  # noqa: E402
from gate_hook import load_gate_config  # noqa: E402

CheckResult = checks.CheckResult

MAX_TEST_PLAN_ENTRIES = 10
MAX_LISTED_ITEMS = 5  # how many untested functions / missing cases to name in a reason

# Files/dirs exempt from the test plan requirement
_TEST_PLAN_EXEMPT = re.compile(
    r"(^|/)(hooks|scripts|migrations|\.github|templates|config|docs|static|shared|\.scratch|\.session|\.gates)(/|$)"
)
_TEST_FILE_RE = re.compile(
    r"(test_|_test\.|\.test\.|\.spec\.|tests/|__tests__/|spec/)", re.IGNORECASE
)
_NON_SOURCE_EXTENSIONS = re.compile(
    r"\.(md|txt|json|yml|yaml|toml|cfg|ini|env|lock|gitignore|dockerignore)$", re.IGNORECASE
)


# --- Decision: each helper returns the reasons it finds ---------------------


def _findings_reasons(findings: dict) -> list[str]:
    """Reasons from the agent's own findings fields."""
    reasons: list[str] = []
    instr = findings["instructions"]
    if instr["addressed"] < instr["total"]:
        reasons.append(f"instructions: {instr['addressed']}/{instr['total']} addressed")
    if findings["rules"]["violations"] > 0:
        reasons.append(f"rules: {findings['rules']['violations']} violation(s)")
    if not findings["readme"]["passed"]:
        reasons.append("readme: validation failed")
    if findings["tests_meaningful"]["result"] == "sloppy":
        reasons.append("test quality: sloppy tests detected")
    if findings["app_verification"]["status"] == "pending":
        reasons.append("app verification: still pending")
    return reasons


def _session_audit_reasons(findings: dict, session_audit: dict | None, config: dict | None) -> list[str]:
    """Reasons where session evidence contradicts the agent's self-report."""
    if not session_audit or not session_audit.get("available"):
        return []
    from mode_resolver import resolve_mode_from_config

    reasons: list[str] = []
    claimed_done = findings["app_verification"]["status"] == "done"
    no_server = not session_audit.get("server_started") and not session_audit.get("http_request_made")
    if claimed_done and no_server:
        reasons.append(
            "app verification: no server/HTTP activity in session — "
            "agent claimed 'done' but no server start or HTTP request found"
        )

    mode = resolve_mode_from_config(config or {})
    if mode.tdd and not session_audit.get("tdd_order_respected", True):
        reasons.append(
            "TDD violation: source files edited before test files — write failing tests first"
        )
    if mode.plan and not session_audit.get("test_plan_before_source", True):
        reasons.append(
            "test plan written after source edits — "
            "write .scratch/test-plan_<slug>.json BEFORE implementing"
        )

    hollow = session_audit.get("skill_adherence", {}).get("hollow", [])
    if hollow:
        reasons.append(
            f"hollow skill invocation: {', '.join(hollow)} — "
            "skill was launched but SKILL.md was never read"
        )
    return reasons


def _skill_invocation_reasons(session_audit_skills: dict | None) -> list[str]:
    """/precommit must appear in the session JSONL."""
    if not session_audit_skills or not session_audit_skills.get("available"):
        return []
    if "precommit" in session_audit_skills.get("skills_invoked", []):
        return []
    return [
        "precommit skill not invoked — findings.json was hand-written "
        "without running /precommit via the Skill tool"
    ]


def _diff_reasons(
    untested_functions: list[str] | None,
    noqa_in_tests: list[str] | None,
    tautological_tests: list[str] | None = None,
) -> list[str]:
    """Reasons from the git diff scan."""
    reasons: list[str] = []
    if untested_functions:
        reasons.append(
            f"TDD: {len(untested_functions)} new function(s) without tests — "
            + "; ".join(untested_functions[:MAX_LISTED_ITEMS])
        )
    if noqa_in_tests:
        reasons.append(
            f"noqa in tests: {len(noqa_in_tests)} suppression(s) added to test files — "
            "fix the lint issue, don't suppress it"
        )
    if tautological_tests:
        reasons.append(
            f"tautological tests: {len(tautological_tests)} assertion(s) that cannot fail — "
            + "; ".join(tautological_tests[:MAX_LISTED_ITEMS])
            + " — expected values must come from a literal, a worked example or the spec"
        )
    return reasons


def _decide_precommit(
    findings: dict,
    test: CheckResult,
    lint: CheckResult,
    session_audit: dict | None = None,
    untested_functions: list[str] | None = None,
    noqa_in_tests: list[str] | None = None,
    config: dict | None = None,
    session_audit_skills: dict | None = None,
    tautological_tests: list[str] | None = None,
) -> tuple[bool, list[str]]:
    reasons = (
        checks.mechanical_reasons(test, lint)
        + _findings_reasons(findings)
        + _session_audit_reasons(findings, session_audit, config)
        + _skill_invocation_reasons(session_audit_skills)
        + _diff_reasons(untested_functions, noqa_in_tests, tautological_tests)
    )
    return (len(reasons) == 0), reasons


# --- Test plans -------------------------------------------------------------


def _changed_source_files(diff_text: str) -> list[str]:
    """Non-test, non-exempt source paths named in a unified diff."""
    changed: list[str] = []
    for line in diff_text.split("\n"):
        if not line.startswith("diff --git"):
            continue
        match = re.search(r"b/(.+)$", line)
        if not match:
            continue
        filepath = match.group(1)
        if _TEST_FILE_RE.search(filepath) or _TEST_PLAN_EXEMPT.search(filepath):
            continue
        if _NON_SOURCE_EXTENSIONS.search(filepath):
            continue
        changed.append(filepath)
    return changed


def _require_test_plan(project_dir: Path, diff_text: str) -> dict:
    """Block when source files were edited but no test plan exists anywhere."""
    not_blocked = {"blocked": False, "reasons": []}
    if not diff_text.strip() or not _changed_source_files(diff_text):
        return not_blocked

    scratch = project_dir / ".scratch"
    if scratch.is_dir() and list(scratch.glob("test-plan_*.json")):
        return not_blocked

    state_file = project_dir / "project-state.md"
    if state_file.is_file():
        content = state_file.read_text(encoding="utf-8", errors="replace")
        if "## Test Plans" in content and "### " in content[content.index("## Test Plans"):]:
            return not_blocked

    return {
        "blocked": True,
        "reasons": [
            "test plan required: source files were edited but no test plan found. "
            "Write .scratch/test-plan_<slug>.json before implementing. "
            "See /implementation Step 4 for the schema."
        ],
    }


def _check_test_plans(project_dir: Path) -> dict:
    """Validate .scratch/test-plan_*.json and their coverage.

    Returns {blocked, reasons, plans} where plans are the valid ones (for cleanup).
    """
    scratch = project_dir / ".scratch"
    plan_files = sorted(scratch.glob("test-plan_*.json")) if scratch.is_dir() else []
    reasons: list[str] = []
    valid_plans: list[dict] = []

    for plan_file in plan_files:
        try:
            plan = json.loads(plan_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            reasons.append(f"test plan: cannot read {plan_file.name}")
            continue
        errors = validate_test_plan(plan)
        if errors:
            reasons.append(f"test plan {plan_file.name}: invalid — {'; '.join(errors)}")
            continue
        missing = check_test_plan_coverage(plan, project_dir)
        if missing:
            reasons.append(
                f"test plan '{plan['feature']}': {len(missing)} case(s) not covered — "
                + "; ".join(missing[:MAX_LISTED_ITEMS])
            )
        else:
            valid_plans.append(plan)

    return {"blocked": len(reasons) > 0, "reasons": reasons, "plans": valid_plans}


def _compress_test_plans_section(content: str) -> str:
    """Keep the last MAX_TEST_PLAN_ENTRIES '### ' entries under '## Test Plans'."""
    marker = "## Test Plans"
    if marker not in content:
        return content

    before, after = content.split(marker, 1)
    next_section = after.find("\n## ", 1)
    plans_text = after if next_section == -1 else after[:next_section]
    remainder = "" if next_section == -1 else after[next_section:]

    entries: list[str] = []
    current: list[str] = []
    for line in plans_text.split("\n"):
        if line.startswith("### ") and current:
            entries.append("\n".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        entries.append("\n".join(current))
    entries = [e for e in entries if e.strip() and "### " in e]

    if len(entries) <= MAX_TEST_PLAN_ENTRIES:
        return content

    archived_count = len(entries) - MAX_TEST_PLAN_ENTRIES
    kept = entries[-MAX_TEST_PLAN_ENTRIES:]
    compressed = (
        f"{marker}\n\n*({archived_count} older test plan(s) archived)*\n\n"
        + "\n\n".join(kept) + "\n"
    )
    return before + compressed + remainder


def _cleanup_test_plans(project_dir: Path, plans: list[dict]) -> None:
    """Append plan summaries to project-state.md, then delete the plan files."""
    state_file = project_dir / "project-state.md"
    summaries = [format_test_plan_summary(plan) for plan in plans]

    if summaries and state_file.is_file():
        content = state_file.read_text(encoding="utf-8")
        if "## Test Plans" not in content:
            content += "\n\n## Test Plans\n"
        content += "\n" + "\n\n".join(summaries) + "\n"
        state_file.write_text(_compress_test_plans_section(content), encoding="utf-8")

    for plan_file in (project_dir / ".scratch").glob("test-plan_*.json"):
        try:
            plan_file.unlink()
        except OSError as exc:
            sys.stderr.write(f"finalize_report: could not remove {plan_file.name}: {exc}\n")


def _append_session_summary(project_dir: Path) -> None:
    """Generate and append a session summary to project-state.md (non-blocking)."""
    state_file = project_dir / "project-state.md"
    if not state_file.is_file():
        return
    try:
        from hooks.session_log import find_latest_session_log

        log_path = find_latest_session_log()
        if not log_path:
            return
        summary = generate_session_summary(log_path)
        if "No toolkit activity" in summary or "unavailable" in summary.lower():
            return

        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        summary = summary.replace("## Session Summary", f"## Session Summary ({date})")
        content = state_file.read_text(encoding="utf-8")
        if "## Session Summary" in content:
            content = re.sub(
                r"## Session Summary[^\n]*\n(?:(?!^## ).)*",
                summary + "\n\n", content, count=1, flags=re.MULTILINE | re.DOTALL,
            )
        else:
            content += "\n\n" + summary + "\n"
        state_file.write_text(content, encoding="utf-8")
    except Exception as exc:  # Non-critical — don't block the gate, but say so
        sys.stderr.write(f"finalize_report: session summary not appended to project-state.md: {exc}\n")


# --- Diff, execution plan, report -------------------------------------------


def _collect_diff_checks(project_dir: Path) -> dict:
    """Staged diff (or unstaged fallback) plus the TDD/noqa/UI scans over it."""
    diff_text = checks._git_output(project_dir, ["diff", "--cached", "--unified=0"])
    if not diff_text.strip():
        diff_text = checks._git_output(project_dir, ["diff", "HEAD", "--unified=0"])
    return {
        "diff_text": diff_text,
        "untested": check_diff_for_untested_functions(diff_text),
        "noqa_in_tests": check_diff_for_noqa_in_tests(diff_text),
        "tautological": check_diff_for_tautological_tests(diff_text),
        "ui_without_e2e": check_diff_for_ui_without_e2e(diff_text),
    }


def _changed_files_for_spot_check(project_dir: Path) -> list[str]:
    """Absolute paths of changed, non-dot files (input for the random spot check)."""
    names = checks._git_output(project_dir, ["diff", "--name-only", "HEAD"])
    return [
        str(project_dir / name.strip())
        for name in names.strip().split("\n")
        if name.strip() and not name.strip().startswith(".")
    ]


def _apply_execution_plan_check(project_dir: Path, ready: bool, reasons: list[str]) -> bool:
    """Verify every planned skill ran; delete the plan on a clean pass. Returns ready."""
    exec_plan_file = project_dir / ".scratch" / "execution-plan.json"
    if not exec_plan_file.is_file():
        return ready
    try:
        exec_plan = json.loads(exec_plan_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        reasons.append("execution plan: cannot read .scratch/execution-plan.json")
        return ready

    plan_errors = validate_execution_plan(exec_plan)
    if plan_errors:
        reasons.append(f"execution plan invalid: {'; '.join(plan_errors)}")
        return False

    skill_audit = checks._check_session_audit()
    skills_from_audit = skill_audit.get("skills_invoked", []) if skill_audit.get("available") else []
    compliance = check_execution_plan_compliance(exec_plan, skills_from_audit)
    if compliance["blocked"]:
        reasons.extend(compliance["reasons"])
        return False

    if ready:
        try:
            exec_plan_file.unlink()
        except OSError as exc:
            sys.stderr.write(f"finalize_report: could not remove execution plan: {exc}\n")
    return ready


def _policy_reasons(
    project_dir: Path, findings: dict, mode_name: str, action_audit: dict, diff_text: str,
) -> tuple[list[str], dict]:
    """Blocking reasons from test plans, stamps and review depth.

    Returns (reasons, test_plan_results) — the plans are needed for cleanup.
    """
    reasons: list[str] = []
    test_plan_results = _check_test_plans(project_dir)
    reasons.extend(test_plan_results["reasons"])
    reasons.extend(_require_test_plan(project_dir, diff_text)["reasons"])
    reasons.extend(checks._check_stamps(project_dir, findings))

    reviewer_stamp_exists = (project_dir / ".gates" / "stamps" / "reviewer").is_file()
    reasons.extend(checks._check_review_depth(
        action_audit or {}, mode_name, reviewer_stamp=reviewer_stamp_exists,
    ))
    return reasons, test_plan_results


def _write_precommit_report(
    project_dir: Path, slug: str, report_id: str, markdown: str, session_audit: dict,
) -> Path:
    """Write the precommit report, appending session-audit warnings when present."""
    if session_audit.get("warnings"):
        audit_section = "\n\n## Session Audit (automated)\n\n"
        for w in session_audit["warnings"]:
            audit_section += f"- ⚠ {w}\n"
        audit_section += f"\nSkills invoked: {session_audit.get('skills_invoked', [])}\n"
        markdown += audit_section
    out_path = checks._report_path(project_dir, "precommit", slug, report_id)
    out_path.write_text(markdown, encoding="utf-8")
    return out_path


def finalize_precommit(project_dir: Path, findings_path: Path) -> int:
    findings = validate_precommit_findings(read_findings(findings_path))
    config = load_gate_config(project_dir)
    test, lint = checks._run_mechanical(project_dir, config)

    from mode_resolver import resolve_mode_from_config
    current_mode = resolve_mode_from_config(config or {})

    action_audit = checks._get_session_action_audit()
    diff = _collect_diff_checks(project_dir)
    skill_audit = checks._check_session_audit()

    ready, reasons = _decide_precommit(
        findings, test, lint, session_audit=action_audit,
        untested_functions=diff["untested"], noqa_in_tests=diff["noqa_in_tests"],
        tautological_tests=diff["tautological"],
        config=config, session_audit_skills=skill_audit,
    )

    # Non-blocking warnings: random spot check, UI changes without E2E
    for w in checks._maybe_spot_check(_changed_files_for_spot_check(project_dir), current_mode.name):
        reasons.append(f"SPOT CHECK (non-blocking): {w}")
    for w in diff["ui_without_e2e"]:
        reasons.append(f"UI WARNING (non-blocking): {w}")

    policy_reasons, test_plan_results = _policy_reasons(
        project_dir, findings, current_mode.name, action_audit, diff["diff_text"],
    )
    if policy_reasons:
        ready = False
        reasons.extend(policy_reasons)

    ready = _apply_execution_plan_check(project_dir, ready, reasons)

    session_audit = checks._check_session_audit()
    report_id = uuid.uuid4().hex[:8]
    markdown = compose_precommit_markdown(findings, test, lint, ready, reasons, report_id)
    out_path = _write_precommit_report(project_dir, findings["slug"], report_id, markdown, session_audit)

    gate_flag = checks._write_gate_flag(project_dir, "precommit") if ready else None
    if ready and test_plan_results.get("plans"):
        _cleanup_test_plans(project_dir, test_plan_results["plans"])
    if ready:
        _append_session_summary(project_dir)

    return checks._emit_response(
        {
            "skill": "precommit",
            "ready_to_commit": ready,
            "report_path": str(out_path.relative_to(project_dir)),
            "report_id": report_id,
            "gate_flag": str(gate_flag.relative_to(project_dir)) if gate_flag else None,
            "mechanical": {"tests_passed": test.passed, "lint_passed": lint.passed},
            "blocking_reasons": reasons,
            "session_audit": session_audit,
        },
        ready,
    )
