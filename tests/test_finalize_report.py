"""Tests for hooks/finalize_report.py — the hook-owned report writer.

Covers:
- findings.json schema validation (precommit)
- mechanical re-run wired through gate/attest helpers
- gate decision: mechanical failures override agent claims
- report file actually written into reports/<skill>/
- exit codes (0 ready, 1 blocked, 2 validation)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / "hooks" / "finalize_report.py"

# Allow direct import of the module's pure functions (no CLI).
sys.path.insert(0, str(REPO_ROOT / "hooks"))
sys.path.insert(0, str(REPO_ROOT))

import finalize_report as fr  # noqa: E402
from gate.attest import CheckResult  # noqa: E402


# --- Fixtures -------------------------------------------------------------


@pytest.fixture
def valid_findings() -> dict:
    return {
        "skill": "precommit",
        "slug": "tidy-imports",
        "instructions": {"addressed": 2, "total": 2, "items": []},
        "rules": {"violations": 0, "items": []},
        "readme": {"passed": True, "details": "23 claims validated"},
        "tests_meaningful": {"result": "verified", "evidence": "asserts outcomes"},
        "app_verification": {"status": "done", "notes": "smoke OK"},
        "summary": "All clear.",
    }


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """A bare project root with a minimal gates.json."""
    (tmp_path / "gates.json").write_text(
        json.dumps({"gate_mode": "legacy", "test_command": "true", "lint_command": "true"})
    )
    return tmp_path


def _write_findings(project_dir: Path, slug: str, findings: dict) -> Path:
    scratch = project_dir / ".scratch" / f"precommit_{slug}"
    scratch.mkdir(parents=True, exist_ok=True)
    p = scratch / "findings.json"
    p.write_text(json.dumps(findings))
    return p


# --- Schema validation ----------------------------------------------------


class TestSchemaValidation:
    def test_accepts_valid_findings(self, valid_findings):
        assert fr._validate_precommit_findings(valid_findings) is valid_findings

    def test_rejects_wrong_skill(self, valid_findings):
        valid_findings["skill"] = "evaluate"
        with pytest.raises(SystemExit) as exc:
            fr._validate_precommit_findings(valid_findings)
        assert exc.value.code == 2

    def test_rejects_missing_required_key(self, valid_findings):
        del valid_findings["rules"]
        with pytest.raises(SystemExit):
            fr._validate_precommit_findings(valid_findings)

    def test_rejects_bad_slug(self, valid_findings):
        valid_findings["slug"] = "Has Caps and Spaces"
        with pytest.raises(SystemExit):
            fr._validate_precommit_findings(valid_findings)

    def test_rejects_addressed_exceeds_total(self, valid_findings):
        valid_findings["instructions"] = {"addressed": 5, "total": 3}
        with pytest.raises(SystemExit):
            fr._validate_precommit_findings(valid_findings)

    def test_rejects_unknown_tests_meaningful_result(self, valid_findings):
        valid_findings["tests_meaningful"]["result"] = "great"
        with pytest.raises(SystemExit):
            fr._validate_precommit_findings(valid_findings)

    def test_rejects_unknown_app_verification_status(self, valid_findings):
        valid_findings["app_verification"]["status"] = "yes"
        with pytest.raises(SystemExit):
            fr._validate_precommit_findings(valid_findings)

    def test_rejects_wrong_type(self, valid_findings):
        valid_findings["readme"]["passed"] = "true"  # string, not bool
        with pytest.raises(SystemExit):
            fr._validate_precommit_findings(valid_findings)


# --- Gate decision (mechanical truth wins) --------------------------------


class TestDecideGate:
    def test_ready_when_everything_passes(self, valid_findings):
        ready, reasons = fr._decide_precommit(
            valid_findings,
            CheckResult("tests", True),
            CheckResult("lint", True),
        )
        assert ready is True
        assert reasons == []

    def test_blocks_on_test_failure_regardless_of_findings(self, valid_findings):
        ready, reasons = fr._decide_precommit(
            valid_findings,
            CheckResult("tests", False, "3 failed"),
            CheckResult("lint", True),
        )
        assert ready is False
        assert any("test re-run failed" in r for r in reasons)

    def test_blocks_on_lint_failure(self, valid_findings):
        ready, reasons = fr._decide_precommit(
            valid_findings,
            CheckResult("tests", True),
            CheckResult("lint", False),
        )
        assert ready is False
        assert any("lint re-run failed" in r for r in reasons)

    def test_blocks_on_unaddressed_instructions(self, valid_findings):
        valid_findings["instructions"] = {"addressed": 1, "total": 3}
        ready, reasons = fr._decide_precommit(
            valid_findings,
            CheckResult("tests", True),
            CheckResult("lint", True),
        )
        assert ready is False
        assert any("instructions" in r for r in reasons)

    def test_blocks_on_rule_violations(self, valid_findings):
        valid_findings["rules"]["violations"] = 2
        ready, _ = fr._decide_precommit(
            valid_findings, CheckResult("tests", True), CheckResult("lint", True)
        )
        assert ready is False

    def test_blocks_on_failed_readme(self, valid_findings):
        valid_findings["readme"]["passed"] = False
        ready, _ = fr._decide_precommit(
            valid_findings, CheckResult("tests", True), CheckResult("lint", True)
        )
        assert ready is False

    def test_blocks_on_sloppy_tests(self, valid_findings):
        valid_findings["tests_meaningful"]["result"] = "sloppy"
        ready, _ = fr._decide_precommit(
            valid_findings, CheckResult("tests", True), CheckResult("lint", True)
        )
        assert ready is False

    def test_blocks_on_pending_app_verification(self, valid_findings):
        valid_findings["app_verification"]["status"] = "pending"
        ready, _ = fr._decide_precommit(
            valid_findings, CheckResult("tests", True), CheckResult("lint", True)
        )
        assert ready is False


# --- End-to-end: hook writes report into reports/ --------------------------


class TestEndToEnd:
    def test_writes_report_and_returns_ready(
        self, project_dir: Path, valid_findings: dict, monkeypatch
    ):
        findings_path = _write_findings(project_dir, valid_findings["slug"], valid_findings)
        monkeypatch.chdir(project_dir)

        # Stub mechanical checks to pass without invoking real subprocesses
        with patch.object(
            fr, "detect_and_run_tests",
            return_value=CheckResult("tests", True, "all pass"),
        ), patch.object(
            fr, "detect_and_run_lint",
            return_value=CheckResult("lint", True, "clean"),
        ):
            exit_code = fr.finalize_precommit(project_dir, findings_path)

        assert exit_code == 0
        # Report file exists in the expected place
        reports = list((project_dir / "reports" / "precommit").glob("pc_*.md"))
        assert len(reports) == 1
        text = reports[0].read_text()
        assert "READY TO COMMIT" in text
        assert "writer: hooks/finalize_report.py" in text
        assert valid_findings["slug"] in reports[0].name

    def test_writes_blocked_report_when_tests_fail(
        self, project_dir: Path, valid_findings: dict, monkeypatch
    ):
        findings_path = _write_findings(project_dir, valid_findings["slug"], valid_findings)
        monkeypatch.chdir(project_dir)

        with patch.object(
            fr, "detect_and_run_tests",
            return_value=CheckResult("python3 -m pytest", False, "1 failed"),
        ), patch.object(
            fr, "detect_and_run_lint",
            return_value=CheckResult("lint", True, "clean"),
        ):
            exit_code = fr.finalize_precommit(project_dir, findings_path)

        assert exit_code == 1
        reports = list((project_dir / "reports" / "precommit").glob("pc_*.md"))
        assert len(reports) == 1
        text = reports[0].read_text()
        assert "[x] BLOCKED" in text
        assert "test re-run failed" in text

    def test_invalid_findings_exits_2(self, project_dir: Path, monkeypatch):
        findings_path = _write_findings(
            project_dir, "bogus", {"skill": "precommit"}  # missing required keys
        )
        monkeypatch.chdir(project_dir)
        with pytest.raises(SystemExit) as exc:
            fr.finalize_precommit(project_dir, findings_path)
        assert exc.value.code == 2

    def test_missing_findings_file_exits_2(self, project_dir: Path, monkeypatch):
        monkeypatch.chdir(project_dir)
        with pytest.raises(SystemExit) as exc:
            fr.finalize_precommit(project_dir, project_dir / "nope.json")
        assert exc.value.code == 2


# --- CLI: invoked as subprocess (proves the actual entry point works) -----


class TestCLI:
    def test_unknown_skill_rejected(self, tmp_path: Path):
        findings = tmp_path / "f.json"
        findings.write_text("{}")
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "evaluate", str(findings)],
            capture_output=True, text=True, cwd=tmp_path,
        )
        assert result.returncode == 2
        assert "not yet supported" in result.stderr

    def test_bad_usage_rejected(self, tmp_path: Path):
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH)],
            capture_output=True, text=True, cwd=tmp_path,
        )
        assert result.returncode == 2
        assert "usage:" in result.stderr

    def test_precommit_writes_report_via_cli(
        self, project_dir: Path, valid_findings: dict
    ):
        findings_path = _write_findings(project_dir, valid_findings["slug"], valid_findings)
        # Use `true` for both commands — they exit 0 reliably.
        # (gates.json fixture already sets this.)
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "precommit", str(findings_path)],
            capture_output=True, text=True, cwd=project_dir,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["ready_to_commit"] is True
        assert payload["report_path"].startswith("reports/precommit/pc_")
        # File exists
        assert (project_dir / payload["report_path"]).is_file()
