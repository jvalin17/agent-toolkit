#!/usr/bin/env python3
"""Tests for scripts/ci-generate-reports.py — fresh mechanical reports for CI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ci-generate-reports.py"


def _make_project(tmp_path: Path, test_command: str = "true", lint_command: str = "true") -> Path:
    """Create a minimal project dir with gates.json."""
    (tmp_path / "gates.json").write_text(json.dumps({
        "gate_mode": "legacy",
        "test_command": test_command,
        "lint_command": lint_command,
        "eval_threshold": 80,
    }))
    # Need a git repo for finalize_report to work
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, capture_output=True)
    (tmp_path / "hello.py").write_text("print('hello')\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, capture_output=True)
    return tmp_path


class TestCiGenerateReports:
    def test_ci_generate_reports_creates_all_four(self, tmp_path):
        """Script generates precommit, evaluate, reviewer, assess reports."""
        project = _make_project(tmp_path)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(project)],
            capture_output=True, text=True, cwd=project,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        # All four report dirs should have at least one report
        for skill in ["precommit", "evaluate", "reviewer", "assess"]:
            reports = list((project / "reports" / skill).glob("*.md"))
            assert len(reports) >= 1, f"No {skill} report generated"

    def test_ci_generate_reports_precommit_passes(self, tmp_path):
        """Generated precommit report should say READY TO COMMIT."""
        project = _make_project(tmp_path)
        subprocess.run(
            [sys.executable, str(SCRIPT), str(project)],
            capture_output=True, text=True, cwd=project,
        )
        reports = list((project / "reports" / "precommit").glob("pc_*.md"))
        text = reports[0].read_text()
        assert "READY TO COMMIT" in text

    def test_ci_generate_reports_evaluate_has_score(self, tmp_path):
        """Generated evaluate report should contain a percentage score."""
        project = _make_project(tmp_path)
        subprocess.run(
            [sys.executable, str(SCRIPT), str(project)],
            capture_output=True, text=True, cwd=project,
        )
        reports = list((project / "reports" / "evaluate").glob("eval_*.md"))
        text = reports[0].read_text()
        assert "Score:" in text
        assert "%" in text

    def test_ci_generate_reports_writes_gate_flags(self, tmp_path):
        """Script should write .gates/ flags for passing skills."""
        project = _make_project(tmp_path)
        subprocess.run(
            [sys.executable, str(SCRIPT), str(project)],
            capture_output=True, text=True, cwd=project,
        )
        assert (project / ".gates" / "precommit-passed").is_file()

    def test_ci_generate_reports_fails_when_tests_fail(self, tmp_path):
        """If tests fail, precommit report should be BLOCKED."""
        project = _make_project(tmp_path, test_command="false")
        # Remove any pre-existing gate flags
        import shutil
        gates_dir = project / ".gates"
        if gates_dir.exists():
            shutil.rmtree(gates_dir)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(project)],
            capture_output=True, text=True, cwd=project,
        )
        # Script should still exit 0 (reports generated) but precommit should be blocked
        reports = list((project / "reports" / "precommit").glob("pc_*.md"))
        text = reports[0].read_text()
        assert "BLOCKED" in text
