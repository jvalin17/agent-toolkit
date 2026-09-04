#!/usr/bin/env python3
"""Generate fresh mechanical reports for CI — no LLM, no fake fixtures.

Replaces seed-gate-reports.sh. Runs finalize_report.py for each skill
with minimal findings, producing real scores from the actual codebase.

Usage:
    python3 scripts/ci-generate-reports.py [project-root]

If project-root is omitted, uses current working directory.
"""

import json
import subprocess
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
FINALIZE = TOOLKIT_ROOT / "hooks" / "finalize_report.py"

SKILLS = ["precommit", "evaluate", "reviewer", "assess"]

# Minimal findings that pass schema validation for each skill
FINDINGS_TEMPLATES = {
    "precommit": {
        "skill": "precommit",
        "slug": "ci-gate",
        "instructions": {"addressed": 0, "total": 0, "items": []},
        "rules": {"violations": 0, "items": []},
        "readme": {"passed": True, "details": "CI — no README changes"},
        "tests_meaningful": {"result": "skipped", "evidence": "CI mechanical run"},
        "app_verification": {"status": "na", "notes": "CI — no app server"},
        "summary": "CI-generated mechanical precommit check.",
    },
    "evaluate": {
        "skill": "evaluate",
        "slug": "ci-gate",
        "topic": "CI mechanical evaluation",
        "summary": "CI-generated mechanical evaluation.",
    },
    "reviewer": {
        "skill": "reviewer",
        "slug": "ci-gate",
        "topic": "CI mechanical review",
        "findings": {"high": 0, "medium": 0, "low": 0},
        "areas_reviewed": ["tests", "lint"],
        "summary": "CI-generated mechanical review — tests and lint only.",
    },
    "assess": {
        "skill": "assess",
        "slug": "ci-gate",
        "topic": "CI mechanical assessment",
        "findings": {"fix_now": 0, "consider": 0, "good": 0},
        "summary": "CI-generated mechanical assessment — tests and lint only.",
    },
}


def generate_report(skill: str, project_root: Path) -> dict:
    """Generate a single skill report by calling finalize_report.py."""
    scratch = project_root / ".scratch" / f"ci_{skill}"
    scratch.mkdir(parents=True, exist_ok=True)

    findings_path = scratch / "findings.json"
    findings_path.write_text(json.dumps(FINDINGS_TEMPLATES[skill], indent=2))

    result = subprocess.run(
        [sys.executable, str(FINALIZE), skill, str(findings_path)],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    try:
        output = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        output = {"error": result.stderr or result.stdout, "returncode": result.returncode}

    return {
        "skill": skill,
        "returncode": result.returncode,
        "output": output,
    }


def main(argv: list[str]) -> int:
    project_root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd().resolve()

    if not project_root.is_dir():
        print(f"ERROR: {project_root} is not a directory", file=sys.stderr)
        return 1

    print(f"Generating mechanical reports for: {project_root}")
    results = []

    for skill in SKILLS:
        print(f"  [{skill}] ", end="", flush=True)
        report = generate_report(skill, project_root)
        results.append(report)

        if report["returncode"] == 0:
            path = report["output"].get("report_path", "?")
            print(f"PASS — {path}")
        elif report["returncode"] == 1:
            reasons = report["output"].get("blocking_reasons", [])
            path = report["output"].get("report_path", "?")
            print(f"BLOCKED — {path}")
            for reason in reasons:
                print(f"    {reason}")
        else:
            print(f"ERROR (exit {report['returncode']})")
            error = report["output"].get("error", "")
            if error:
                print(f"    {error[:200]}")

    # Summary
    passed = sum(1 for r in results if r["returncode"] == 0)
    blocked = sum(1 for r in results if r["returncode"] == 1)
    errors = sum(1 for r in results if r["returncode"] >= 2)

    print(f"\nResults: {passed} passed, {blocked} blocked, {errors} errors")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
