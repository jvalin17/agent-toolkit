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

        gate_flag = project_dir / ".gates" / "precommit-passed"
        assert gate_flag.is_file()
        assert "READY" in gate_flag.read_text()

    def test_does_not_write_gate_when_blocked(
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
        assert not (project_dir / ".gates" / "precommit-passed").exists()

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

    def test_main_resolves_project_from_scratch_not_cwd(
        self, project_dir: Path, valid_findings: dict, monkeypatch, tmp_path: Path
    ):
        findings_path = _write_findings(project_dir, valid_findings["slug"], valid_findings)
        elsewhere = tmp_path / "wrong-cwd"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)

        with patch.object(
            fr, "detect_and_run_tests",
            return_value=CheckResult("tests", True, "ok"),
        ) as mock_tests, patch.object(
            fr, "detect_and_run_lint",
            return_value=CheckResult("lint", True, "ok"),
        ):
            exit_code = fr.main(
                ["finalize_report.py", "precommit", str(findings_path)]
            )

        assert exit_code == 0
        mock_tests.assert_called_once()
        assert mock_tests.call_args[0][0] == project_dir


# --- CLI: invoked as subprocess (proves the actual entry point works) -----


class TestCLI:
    def test_unsupported_skill_rejected(self, tmp_path: Path):
        findings = tmp_path / "f.json"
        findings.write_text("{}")
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "deploy", str(findings)],
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


# --- Evaluate skill -------------------------------------------------------


EVAL_DIMENSIONS = {
    "completeness": 92,
    "code_quality": 82,
    "security": 91,
    "test_quality": 94,
    "efficiency": 84,
}


@pytest.fixture
def valid_evaluate_findings() -> dict:
    return {
        "skill": "evaluate",
        "slug": "repo-eval",
        "topic": "agent-toolkit",
        "dimensions": dict(EVAL_DIMENSIONS),
        "summary": "Solid repo; evaluate gate unlock needed.",
    }


def _write_evaluate_findings(project_dir: Path, slug: str, findings: dict) -> Path:
    scratch = project_dir / ".scratch" / f"evaluate_{slug}"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "findings.json"
    path.write_text(json.dumps(findings))
    return path


class TestEvaluateSchemaValidation:
    def test_accepts_valid_findings(self, valid_evaluate_findings):
        assert fr._validate_evaluate_findings(valid_evaluate_findings) is valid_evaluate_findings

    def test_rejects_wrong_skill(self, valid_evaluate_findings):
        valid_evaluate_findings["skill"] = "precommit"
        with pytest.raises(SystemExit) as exc:
            fr._validate_evaluate_findings(valid_evaluate_findings)
        assert exc.value.code == 2

    def test_rejects_missing_dimension(self, valid_evaluate_findings):
        del valid_evaluate_findings["dimensions"]["security"]
        with pytest.raises(SystemExit):
            fr._validate_evaluate_findings(valid_evaluate_findings)

    def test_rejects_score_out_of_range(self, valid_evaluate_findings):
        valid_evaluate_findings["dimensions"]["completeness"] = 101
        with pytest.raises(SystemExit):
            fr._validate_evaluate_findings(valid_evaluate_findings)


class TestEvaluateScore:
    def test_compute_weighted_overall(self):
        score = fr._compute_evaluate_score(EVAL_DIMENSIONS)
        # 92*0.3 + 82*0.25 + 91*0.2 + 94*0.15 + 84*0.1 = 89.3 -> 89
        assert score == 89

    def test_passes_at_threshold(self, valid_evaluate_findings):
        valid_evaluate_findings["dimensions"] = {k: 96 for k in EVAL_DIMENSIONS}
        passed, score, reasons = fr._decide_evaluate(
            valid_evaluate_findings,
            CheckResult("tests", True),
            CheckResult("lint", True),
            threshold=95,
        )
        assert passed is True
        assert score >= 95
        assert reasons == []

    def test_blocks_below_threshold(self, valid_evaluate_findings):
        passed, score, reasons = fr._decide_evaluate(
            valid_evaluate_findings,
            CheckResult("tests", True),
            CheckResult("lint", True),
            threshold=95,
        )
        assert passed is False
        assert score == 89
        assert any("below threshold" in r for r in reasons)

    def test_blocks_on_mechanical_test_failure(self, valid_evaluate_findings):
        valid_evaluate_findings["dimensions"] = {k: 100 for k in EVAL_DIMENSIONS}
        passed, _, reasons = fr._decide_evaluate(
            valid_evaluate_findings,
            CheckResult("tests", False, "fail"),
            CheckResult("lint", True),
            threshold=95,
        )
        assert passed is False
        assert any("test re-run failed" in r for r in reasons)


class TestEvaluateEndToEnd:
    def test_writes_report_and_gate_when_passed(
        self, project_dir: Path, valid_evaluate_findings: dict, monkeypatch
    ):
        (project_dir / "gates.json").write_text(
            json.dumps({"eval_threshold": 95, "test_command": "true", "lint_command": "true"})
        )
        valid_evaluate_findings["dimensions"] = {k: 96 for k in EVAL_DIMENSIONS}
        findings_path = _write_evaluate_findings(
            project_dir, valid_evaluate_findings["slug"], valid_evaluate_findings
        )
        monkeypatch.chdir(project_dir)

        with patch.object(
            fr, "detect_and_run_tests", return_value=CheckResult("tests", True)
        ), patch.object(
            fr, "detect_and_run_lint", return_value=CheckResult("lint", True)
        ):
            exit_code = fr.finalize_evaluate(project_dir, findings_path)

        assert exit_code == 0
        reports = list((project_dir / "reports" / "evaluate").glob("eval_*.md"))
        assert len(reports) == 1
        text = reports[0].read_text()
        assert "# Score: **" in text
        assert "writer: hooks/finalize_report.py" in text

        gate_flag = project_dir / ".gates" / "evaluate-passed"
        assert gate_flag.is_file()
        assert "PASSED" in gate_flag.read_text()
        assert "96" in gate_flag.read_text() or "100" in gate_flag.read_text()

    def test_no_gate_when_below_threshold(
        self, project_dir: Path, valid_evaluate_findings: dict, monkeypatch
    ):
        (project_dir / "gates.json").write_text(
            json.dumps({"eval_threshold": 95, "test_command": "true", "lint_command": "true"})
        )
        findings_path = _write_evaluate_findings(
            project_dir, valid_evaluate_findings["slug"], valid_evaluate_findings
        )
        monkeypatch.chdir(project_dir)

        with patch.object(
            fr, "detect_and_run_tests", return_value=CheckResult("tests", True)
        ), patch.object(
            fr, "detect_and_run_lint", return_value=CheckResult("lint", True)
        ):
            exit_code = fr.finalize_evaluate(project_dir, findings_path)

        assert exit_code == 1
        assert not (project_dir / ".gates" / "evaluate-passed").exists()
        reports = list((project_dir / "reports" / "evaluate").glob("eval_*.md"))
        assert len(reports) == 1
        assert "BLOCKED" in reports[0].read_text()

    def test_main_evaluate_via_cli(self, project_dir: Path, valid_evaluate_findings: dict):
        (project_dir / "gates.json").write_text(
            json.dumps({"eval_threshold": 95, "test_command": "true", "lint_command": "true"})
        )
        valid_evaluate_findings["dimensions"] = {k: 96 for k in EVAL_DIMENSIONS}
        findings_path = _write_evaluate_findings(
            project_dir, valid_evaluate_findings["slug"], valid_evaluate_findings
        )
        result = subprocess.run(
            [sys.executable, str(HOOK_PATH), "evaluate", str(findings_path)],
            capture_output=True,
            text=True,
            cwd=project_dir,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["passed"] is True
        assert payload["score"] >= 95
        assert payload["gate_flag"] == ".gates/evaluate-passed"


# --- Reviewer skill -----------------------------------------------------


@pytest.fixture
def valid_reviewer_findings() -> dict:
    return {
        "skill": "reviewer",
        "slug": "auth-module",
        "topic": "auth module",
        "findings": {"high": 0, "medium": 1, "low": 2},
        "areas_reviewed": ["code quality", "tests"],
        "summary": "One medium finding; no high severity.",
    }


def _write_reviewer_findings(project_dir: Path, slug: str, findings: dict) -> Path:
    scratch = project_dir / ".scratch" / f"reviewer_{slug}"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "findings.json"
    path.write_text(json.dumps(findings))
    return path


class TestReviewerSchemaValidation:
    def test_accepts_valid_findings(self, valid_reviewer_findings):
        assert fr._validate_reviewer_findings(valid_reviewer_findings) is valid_reviewer_findings

    def test_rejects_wrong_skill(self, valid_reviewer_findings):
        valid_reviewer_findings["skill"] = "assess"
        with pytest.raises(SystemExit) as exc:
            fr._validate_reviewer_findings(valid_reviewer_findings)
        assert exc.value.code == 2

    def test_rejects_negative_high_count(self, valid_reviewer_findings):
        valid_reviewer_findings["findings"]["high"] = -1
        with pytest.raises(SystemExit):
            fr._validate_reviewer_findings(valid_reviewer_findings)


class TestReviewerDecision:
    def test_passes_with_no_high_severity(self, valid_reviewer_findings):
        passed, reasons = fr._decide_reviewer(
            valid_reviewer_findings,
            CheckResult("tests", True),
            CheckResult("lint", True),
        )
        assert passed is True
        assert reasons == []

    def test_blocks_on_high_severity(self, valid_reviewer_findings):
        valid_reviewer_findings["findings"]["high"] = 2
        passed, reasons = fr._decide_reviewer(
            valid_reviewer_findings,
            CheckResult("tests", True),
            CheckResult("lint", True),
        )
        assert passed is False
        assert any("high-severity" in r for r in reasons)

    def test_blocks_on_mechanical_failure(self, valid_reviewer_findings):
        passed, reasons = fr._decide_reviewer(
            valid_reviewer_findings,
            CheckResult("tests", False, "fail"),
            CheckResult("lint", True),
        )
        assert passed is False
        assert any("test re-run failed" in r for r in reasons)


class TestReviewerEndToEnd:
    def test_writes_report_and_gate_when_passed(
        self, project_dir: Path, valid_reviewer_findings: dict, monkeypatch
    ):
        findings_path = _write_reviewer_findings(
            project_dir, valid_reviewer_findings["slug"], valid_reviewer_findings
        )
        monkeypatch.chdir(project_dir)

        with patch.object(
            fr, "detect_and_run_tests", return_value=CheckResult("tests", True)
        ), patch.object(
            fr, "detect_and_run_lint", return_value=CheckResult("lint", True)
        ):
            exit_code = fr.finalize_reviewer(project_dir, findings_path)

        assert exit_code == 0
        reports = list((project_dir / "reports" / "reviewer").glob("review_*.md"))
        assert len(reports) == 1
        text = reports[0].read_text()
        assert "PASSED" in text
        assert "writer: hooks/finalize_report.py" in text

        gate_flag = project_dir / ".gates" / "reviewer-passed"
        assert gate_flag.is_file()
        assert "PASSED" in gate_flag.read_text()

    def test_no_gate_when_high_severity(
        self, project_dir: Path, valid_reviewer_findings: dict, monkeypatch
    ):
        valid_reviewer_findings["findings"]["high"] = 1
        findings_path = _write_reviewer_findings(
            project_dir, valid_reviewer_findings["slug"], valid_reviewer_findings
        )
        monkeypatch.chdir(project_dir)

        with patch.object(
            fr, "detect_and_run_tests", return_value=CheckResult("tests", True)
        ), patch.object(
            fr, "detect_and_run_lint", return_value=CheckResult("lint", True)
        ):
            exit_code = fr.finalize_reviewer(project_dir, findings_path)

        assert exit_code == 1
        assert not (project_dir / ".gates" / "reviewer-passed").exists()
        reports = list((project_dir / "reports" / "reviewer").glob("review_*.md"))
        assert "BLOCKED" in reports[0].read_text()
        assert "PASSED —" not in reports[0].read_text()


# --- Assess skill -------------------------------------------------------


@pytest.fixture
def valid_assess_findings() -> dict:
    return {
        "skill": "assess",
        "slug": "api-layer",
        "topic": "API layer fitness",
        "findings": {"fix_now": 0, "consider": 2, "good": 4},
        "summary": "Architecture fit for current scale.",
    }


def _write_assess_findings(project_dir: Path, slug: str, findings: dict) -> Path:
    scratch = project_dir / ".scratch" / f"assess_{slug}"
    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / "findings.json"
    path.write_text(json.dumps(findings))
    return path


class TestAssessSchemaValidation:
    def test_accepts_valid_findings(self, valid_assess_findings):
        assert fr._validate_assess_findings(valid_assess_findings) is valid_assess_findings

    def test_rejects_wrong_skill(self, valid_assess_findings):
        valid_assess_findings["skill"] = "reviewer"
        with pytest.raises(SystemExit) as exc:
            fr._validate_assess_findings(valid_assess_findings)
        assert exc.value.code == 2

    def test_rejects_negative_fix_now(self, valid_assess_findings):
        valid_assess_findings["findings"]["fix_now"] = -1
        with pytest.raises(SystemExit):
            fr._validate_assess_findings(valid_assess_findings)


class TestAssessDecision:
    def test_passes_with_no_critical(self, valid_assess_findings):
        passed, reasons = fr._decide_assess(
            valid_assess_findings,
            CheckResult("tests", True),
            CheckResult("lint", True),
        )
        assert passed is True
        assert reasons == []

    def test_blocks_on_fix_now(self, valid_assess_findings):
        valid_assess_findings["findings"]["fix_now"] = 1
        passed, reasons = fr._decide_assess(
            valid_assess_findings,
            CheckResult("tests", True),
            CheckResult("lint", True),
        )
        assert passed is False
        assert any("fix_now" in r or "critical" in r for r in reasons)


class TestAssessEndToEnd:
    def test_writes_report_and_gate_when_passed(
        self, project_dir: Path, valid_assess_findings: dict, monkeypatch
    ):
        findings_path = _write_assess_findings(
            project_dir, valid_assess_findings["slug"], valid_assess_findings
        )
        monkeypatch.chdir(project_dir)

        with patch.object(
            fr, "detect_and_run_tests", return_value=CheckResult("tests", True)
        ), patch.object(
            fr, "detect_and_run_lint", return_value=CheckResult("lint", True)
        ):
            exit_code = fr.finalize_assess(project_dir, findings_path)

        assert exit_code == 0
        reports = list((project_dir / "reports" / "assess").glob("assess_*.md"))
        assert len(reports) == 1
        text = reports[0].read_text()
        assert "PASSED" in text
        assert "writer: hooks/finalize_report.py" in text

        gate_flag = project_dir / ".gates" / "assess-passed"
        assert gate_flag.is_file()
        assert "PASSED" in gate_flag.read_text()

    def test_no_gate_when_critical(
        self, project_dir: Path, valid_assess_findings: dict, monkeypatch
    ):
        valid_assess_findings["findings"]["fix_now"] = 2
        findings_path = _write_assess_findings(
            project_dir, valid_assess_findings["slug"], valid_assess_findings
        )
        monkeypatch.chdir(project_dir)

        with patch.object(
            fr, "detect_and_run_tests", return_value=CheckResult("tests", True)
        ), patch.object(
            fr, "detect_and_run_lint", return_value=CheckResult("lint", True)
        ):
            exit_code = fr.finalize_assess(project_dir, findings_path)

        assert exit_code == 1
        assert not (project_dir / ".gates" / "assess-passed").exists()
        reports = list((project_dir / "reports" / "assess").glob("assess_*.md"))
        assert "BLOCKED" in reports[0].read_text()
        assert "[!!]" in reports[0].read_text()
