#!/usr/bin/env python3
"""Tests for skill_passed.py — reports gate status after a gated skill runs."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from skill_passed import run_skill_passed  # noqa: E402


@pytest.fixture
def project(tmp_path):
    """Project dir with .gates/ for testing."""
    gates_dir = tmp_path / ".gates"
    gates_dir.mkdir()
    return tmp_path


def make_input(skill: str) -> str:
    return json.dumps({"tool_input": {"skill": skill}})


def parse_context(output: str) -> str:
    """Extract additionalContext from hook response."""
    data = json.loads(output)
    return data["hookSpecificOutput"]["additionalContext"]


class TestGatedSkillPassed:
    def test_precommit_passed_reports_success(self, project):
        (project / ".gates" / "precommit-passed").write_text("READY")
        _, output = run_skill_passed(make_input("precommit"), project)
        context = parse_context(output)
        assert "/precommit PASSED" in context
        assert "gate unlocked" in context

    def test_all_gates_unlocked_message(self, project):
        (project / ".gates" / "precommit-passed").write_text("READY")
        (project / ".gates" / "evaluate-passed").write_text("PASSED 98")
        (project / ".gates" / "reviewer-passed").write_text("PASSED")
        (project / ".gates" / "assess-passed").write_text("PASSED")
        _, output = run_skill_passed(make_input("precommit"), project)
        context = parse_context(output)
        assert "all gates unlocked" in context
        assert "git commit/push is allowed" in context

    def test_reports_remaining_gates(self, project):
        (project / ".gates" / "precommit-passed").write_text("READY")
        _, output = run_skill_passed(make_input("precommit"), project)
        context = parse_context(output)
        assert "/evaluate" in context or "Still needed" in context

    def test_evaluate_passed(self, project):
        (project / ".gates" / "evaluate-passed").write_text("PASSED 98")
        _, output = run_skill_passed(make_input("evaluate"), project)
        context = parse_context(output)
        assert "/evaluate PASSED" in context


class TestGatedSkillNotPassed:
    def test_precommit_not_passed(self, project):
        # No flag file — skill ran but didn't pass
        _, output = run_skill_passed(make_input("precommit"), project)
        context = parse_context(output)
        assert "did NOT pass" in context
        assert "Gate remains locked" in context

    def test_evaluate_not_passed(self, project):
        _, output = run_skill_passed(make_input("evaluate"), project)
        context = parse_context(output)
        assert "did NOT pass" in context


class TestNonGatedSkills:
    def test_implementation_returns_demo_prompt(self, project):
        """F3.2: /implementation now returns demo prompt, not empty."""
        exit_code, output = run_skill_passed(make_input("implementation"), project)
        assert exit_code == 0
        context = parse_context(output)
        assert "DEMO" in context

    def test_debug_ignored(self, project):
        exit_code, output = run_skill_passed(make_input("debug"), project)
        assert exit_code == 0
        assert output == ""

    def test_explore_ignored(self, project):
        exit_code, output = run_skill_passed(make_input("explore"), project)
        assert exit_code == 0
        assert output == ""


class TestEdgeCases:
    def test_empty_input(self, project):
        exit_code, output = run_skill_passed("", project)
        assert exit_code == 0
        assert output == ""

    def test_invalid_json(self, project):
        exit_code, output = run_skill_passed("bad", project)
        assert exit_code == 0
        assert output == ""

    def test_missing_skill_field(self, project):
        exit_code, output = run_skill_passed(json.dumps({"tool_input": {}}), project)
        assert exit_code == 0
        assert output == ""

    def test_empty_skill(self, project):
        exit_code, output = run_skill_passed(make_input(""), project)
        assert exit_code == 0
        assert output == ""


class TestDemoCompleted:
    """F3.2: After /implementation completes, inject demo reminder for new features."""

    def test_implementation_injects_demo_prompt(self, project):
        """After /implementation, skill_passed injects demo reminder."""
        _, output = run_skill_passed(make_input("implementation"), project)
        context = parse_context(output)
        assert "DEMO" in context
        assert "real data" in context.lower()

    def test_demo_prompt_scoped_to_new_features(self, project):
        """Demo prompt tells agent it applies to new features, not fix/refactor."""
        _, output = run_skill_passed(make_input("implementation"), project)
        context = parse_context(output)
        assert "new feature" in context.lower()

    def test_non_implementation_no_demo_prompt(self, project):
        """Other non-gated skills don't inject demo prompt."""
        exit_code, output = run_skill_passed(make_input("explore"), project)
        assert exit_code == 0
        assert output == ""
