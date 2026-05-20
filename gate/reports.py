"""Validate skill reports under reports/ for attestation (facts bound to files)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

SKILL_REPORT_DIRS = {
    "precommit": "precommit",
    "evaluate": "evaluate",
    "reviewer": "reviewer",
    "assess": "assess",
}

PRE_COMMIT_PREFIX = "pc_"
EVAL_PREFIX = "eval_"
REVIEW_PREFIX = "review_"
ASSESS_PREFIX = "assess_"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def latest_report(project_root: Path, skill: str) -> Path | None:
    subdir = SKILL_REPORT_DIRS.get(skill, skill)
    report_dir = project_root / "reports" / subdir
    if not report_dir.is_dir():
        return None
    prefix = {
        "precommit": PRE_COMMIT_PREFIX,
        "evaluate": EVAL_PREFIX,
        "reviewer": REVIEW_PREFIX,
        "assess": ASSESS_PREFIX,
    }.get(skill, "")
    candidates = sorted(
        (p for p in report_dir.glob("*.md") if not prefix or p.name.startswith(prefix)),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _report_block(
    path: Path | None,
    project_root: Path,
    passed: bool,
    detail: str,
    **extra: Any,
) -> dict[str, Any]:
    block: dict[str, Any] = {
        "passed": passed,
        "detail": detail,
        "source": "report_v1",
    }
    if path and path.is_file():
        try:
            block["report_path"] = str(path.relative_to(project_root))
        except ValueError:
            block["report_path"] = str(path)
        block["report_sha256"] = sha256_file(path)
    return {**block, **extra}


def check_precommit_report(project_root: Path, path: Path | None) -> dict[str, Any]:
    if path is None:
        return _report_block(None, project_root, False, "missing reports/precommit/*.md — run /precommit")
    text = path.read_text(encoding="utf-8", errors="replace")
    if "READY TO COMMIT" not in text and "[x] READY TO COMMIT" not in text:
        return _report_block(path, project_root, False, "precommit report missing READY TO COMMIT")
    return _report_block(path, project_root, True, "ok")


def check_evaluate_report(project_root: Path, path: Path | None, threshold: int) -> dict[str, Any]:
    if path is None:
        return _report_block(
            None, project_root, False, "missing reports/evaluate/*.md — run /evaluate",
            overall_score=0, threshold=threshold,
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"#\s*Score:\s*\*?\*?(\d+)%", text, re.I) or re.search(r"Overall\s*\|\s*\*?\*?(\d+)%", text, re.I)
    if not m:
        m = re.search(r"(\d+)%\s*\([A-F]", text)
    if not m:
        return _report_block(
            path, project_root, False, "evaluate report missing Score: N%",
            overall_score=0, threshold=threshold,
        )
    score = int(m.group(1))
    passed = score >= threshold
    detail = "ok" if passed else f"score {score}% < {threshold}%"
    return _report_block(path, project_root, passed, detail, overall_score=score, threshold=threshold)


def check_reviewer_report(project_root: Path, path: Path | None) -> dict[str, Any]:
    if path is None:
        return _report_block(None, project_root, False, "missing reports/reviewer/*.md — run /reviewer")
    text = path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"high[- ]severity", text, re.I) and "PASSED" not in text:
        if re.search(r"high[- ]severity.*[1-9]", text, re.I):
            return _report_block(path, project_root, False, "high-severity findings remain")
    if "PASSED" in text:
        return _report_block(path, project_root, True, "ok")
    if re.search(r"\|\s*\*\*Status\*\*\s*\|\s*completed", text, re.I):
        return _report_block(path, project_root, True, "ok (completed)")
    return _report_block(path, project_root, False, "reviewer report missing PASSED or completed status")


def check_assess_report(project_root: Path, path: Path | None) -> dict[str, Any]:
    if path is None:
        return _report_block(None, project_root, False, "missing reports/assess/*.md — run /assess")
    text = path.read_text(encoding="utf-8", errors="replace")
    if "[!!]" in text and "PASSED" not in text:
        return _report_block(path, project_root, False, "critical [!!] findings remain")
    if "PASSED" in text:
        return _report_block(path, project_root, True, "ok")
    if re.search(r"\|\s*\*\*Status\*\*\s*\|\s*completed", text, re.I):
        return _report_block(path, project_root, True, "ok (completed)")
    return _report_block(path, project_root, False, "assess report missing PASSED or completed status")


def skill_results_from_reports(
    project_root: Path,
    threshold: int,
    mechanical_precommit: dict[str, Any],
) -> dict[str, Any]:
    """Merge mechanical precommit checks with report-backed skill gates."""
    pc_path = latest_report(project_root, "precommit")
    pc = check_precommit_report(project_root, pc_path)
    pc["checks"] = mechanical_precommit.get("checks", [])
    pc["passed"] = bool(mechanical_precommit.get("passed")) and pc["passed"]

    ev_path = latest_report(project_root, "evaluate")
    ev = check_evaluate_report(project_root, ev_path, threshold)

    rv_path = latest_report(project_root, "reviewer")
    rv = check_reviewer_report(project_root, rv_path)

    as_path = latest_report(project_root, "assess")
    assess = check_assess_report(project_root, as_path)

    return {
        "precommit": pc,
        "evaluate": ev,
        "reviewer": rv,
        "assess": assess,
    }
