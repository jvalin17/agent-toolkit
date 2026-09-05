#!/usr/bin/env python3
"""Generate fresh mechanical reports for CI — no LLM, no fake fixtures.

Self-contained: uses only gate/attest.py (shipped in .agent-toolkit/gate/).
Does NOT require finalize_report.py or any other hook files.

Works identically whether called from:
  - Toolkit repo: python scripts/ci-generate-reports.py .
  - Consumer project CI: python .agent-toolkit/scripts/ci-generate-reports.py .

Usage:
    python3 ci-generate-reports.py [project-root]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _find_gate_module(project_root: Path) -> bool:
    """Add gate module to sys.path. Returns True if found."""
    candidates = [
        project_root / ".agent-toolkit",          # consumer project
        Path(__file__).resolve().parent.parent,    # toolkit repo (gate/ is at root)
    ]
    for candidate in candidates:
        gate_dir = candidate / "gate"
        if gate_dir.is_dir() and (gate_dir / "attest.py").is_file():
            sys.path.insert(0, str(candidate))
            return True
    return False


def _load_config(project_root: Path) -> dict:
    """Load gates.json."""
    for candidate in [
        project_root / "gates.json",
        project_root / ".claude" / "gates.json",
    ]:
        if candidate.is_file():
            return json.loads(candidate.read_text())
    return {}


def _write_report(report_dir: Path, prefix: str, lines: list[str]) -> Path:
    """Write a report file and return its path."""
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{prefix}_ci-mechanical_00000000.md"
    path.write_text("\n".join(lines))
    return path


def _write_gate_flag(project_root: Path, skill: str, extra: str = "") -> None:
    """Write a .gates/ flag file."""
    gates_dir = project_root / ".gates"
    gates_dir.mkdir(parents=True, exist_ok=True)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    flag = gates_dir / f"{skill}-passed"
    flag.write_text(f"READY {date} {extra}\n".strip() + "\n")


def generate_precommit(project_root: Path, test_passed: bool, lint_passed: bool,
                       test_name: str, lint_name: str,
                       test_detail: str, lint_detail: str) -> Path:
    passed = test_passed and lint_passed
    status = "[x] READY TO COMMIT" if passed else "[x] BLOCKED"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"<!-- agent-toolkit:precommit | v1 | {date} | ci -->",
        "# Precommit: CI mechanical check",
        "",
        f"**Status:** {status}",
        "**writer:** scripts/ci-generate-reports.py",
        "",
        "## Mechanical Checks",
        "",
        "| Check | Result |",
        "|-------|--------|",
        f"| Tests ({test_name}) | {'PASS' if test_passed else 'FAIL'} |",
        f"| Lint ({lint_name}) | {'PASS' if lint_passed else 'FAIL'} |",
    ]

    if not passed:
        lines += ["", "## Blocking Reasons", ""]
        if not test_passed:
            lines.append(f"- test re-run failed: {test_detail[:200]}")
        if not lint_passed:
            lines.append(f"- lint re-run failed: {lint_detail[:200]}")

    path = _write_report(project_root / "reports" / "precommit", "pc", lines)
    if passed:
        _write_gate_flag(project_root, "precommit")
    return path


def generate_evaluate(project_root: Path, test_passed: bool, lint_passed: bool,
                      config: dict) -> Path:
    # Base score from mechanical checks
    score = 100
    if not test_passed:
        score -= 30
    if not lint_passed:
        score -= 20

    threshold = int(config.get("eval_threshold", 95))
    passed = score >= threshold
    grade = "A+" if score >= 95 else "A" if score >= 90 else "B+" if score >= 85 else "B" if score >= 80 else "C"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"<!-- agent-toolkit:evaluate | v1 | {date} | ci -->",
        "# Evaluation: CI mechanical",
        "",
        f"# Score: **{score}%** ({grade})",
        "",
        "| Dimension | Score |",
        "|-----------|-------|",
        f"| **Overall** | **{score}%** |",
        "",
        f"**Threshold:** {threshold}%",
        f"**Status:** {'PASSED' if passed else 'BLOCKED'}",
        "**writer:** scripts/ci-generate-reports.py",
    ]

    path = _write_report(project_root / "reports" / "evaluate", "eval", lines)
    if passed:
        _write_gate_flag(project_root, "evaluate", f"score={score}")
    return path


def generate_reviewer(project_root: Path, test_passed: bool, lint_passed: bool) -> Path:
    passed = test_passed and lint_passed
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"<!-- agent-toolkit:reviewer | v1 | {date} | ci -->",
        "# Review: CI mechanical",
        "",
        f"**Status:** {'PASSED' if passed else 'BLOCKED'}",
        "",
        "| Severity | Count |",
        "|----------|-------|",
        "| High | 0 |",
        "| Medium | 0 |",
        "| Low | 0 |",
        "",
        "**writer:** scripts/ci-generate-reports.py",
    ]

    path = _write_report(project_root / "reports" / "reviewer", "review", lines)
    if passed:
        _write_gate_flag(project_root, "reviewer")
    return path


def generate_assess(project_root: Path, test_passed: bool, lint_passed: bool) -> Path:
    passed = test_passed and lint_passed
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [
        f"<!-- agent-toolkit:assess | v1 | {date} | ci -->",
        "# Assessment: CI mechanical",
        "",
        f"**Status:** {'PASSED' if passed else 'BLOCKED'}",
        "",
        "| Category | Count |",
        "|----------|-------|",
        "| Fix Now | 0 |",
        "| Consider | 0 |",
        "| Good | 1 |",
        "",
        "**writer:** scripts/ci-generate-reports.py",
    ]

    path = _write_report(project_root / "reports" / "assess", "assess", lines)
    if passed:
        _write_gate_flag(project_root, "assess")
    return path


def main(argv: list[str]) -> int:
    project_root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd().resolve()

    if not project_root.is_dir():
        print(f"ERROR: {project_root} is not a directory", file=sys.stderr)
        return 1

    if not _find_gate_module(project_root):
        print("ERROR: gate module not found in .agent-toolkit/gate/ or ./gate/", file=sys.stderr)
        return 1

    from gate.attest import detect_and_run_lint, detect_and_run_tests

    config = _load_config(project_root)

    print(f"Generating mechanical reports for: {project_root}")

    # Run mechanical checks once
    test = detect_and_run_tests(project_root, config)
    lint = detect_and_run_lint(project_root, config)

    print(f"  Tests: {'PASS' if test.passed else 'FAIL'} ({test.name})")
    print(f"  Lint:  {'PASS' if lint.passed else 'FAIL'} ({lint.name})")

    # Generate all four reports
    pc = generate_precommit(
        project_root, test.passed, lint.passed,
        test.name, lint.name, test.detail, lint.detail,
    )
    print(f"  [precommit] {pc.relative_to(project_root)}")

    ev = generate_evaluate(project_root, test.passed, lint.passed, config)
    print(f"  [evaluate]  {ev.relative_to(project_root)}")

    rv = generate_reviewer(project_root, test.passed, lint.passed)
    print(f"  [reviewer]  {rv.relative_to(project_root)}")

    assess = generate_assess(project_root, test.passed, lint.passed)
    print(f"  [assess]    {assess.relative_to(project_root)}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
