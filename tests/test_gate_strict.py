"""Tests for mode-based gate enforcement in hooks/gate_hook.py.

Tests the new consolidated mode system:
- minimal: no gates
- default: precommit on commit
- safe: precommit on commit, reviewer on push
"""

import json
from pathlib import Path

import pytest

from hooks.gate_hook import run_gate


@pytest.fixture
def project_dir(tmp_path):
    """Project dir with gates.json and .gates/ directory."""
    return tmp_path


def make_hook_input(command: str) -> str:
    """Build the stdin JSON that gate_hook.py expects."""
    return json.dumps({"tool_input": {"command": command}})


def setup_gates_json(project_dir: Path, mode: str = "default"):
    """Write a gates.json with given mode."""
    config = {
        "gate_mode": "legacy",
        "mode": mode,
        "eval_threshold": 95,
    }
    (project_dir / "gates.json").write_text(json.dumps(config))


def write_gate_flag(project_dir: Path, skill: str, content: str):
    """Write a .gates/ flag file."""
    gates_dir = project_dir / ".gates"
    gates_dir.mkdir(exist_ok=True)
    (gates_dir / f"{skill}-passed").write_text(content)


class TestModeBasedGateEnforcement:
    def test_safe_mode_requires_reviewer_for_push(self, project_dir):
        """In safe mode, push requires reviewer."""
        setup_gates_json(project_dir, mode="safe")
        write_gate_flag(project_dir, "precommit", "READY 2026-05-21")

        stdin = make_hook_input("git push origin main")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0
        assert "block" in output
        assert "reviewer" in output.lower()

    def test_safe_mode_allows_push_with_reviewer(self, project_dir):
        """In safe mode, push allowed when reviewer passes."""
        setup_gates_json(project_dir, mode="safe")
        write_gate_flag(project_dir, "reviewer", "PASSED 2026-05-21")

        stdin = make_hook_input("git push origin main")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0
        assert output == ""

    def test_safe_mode_requires_precommit_for_commit(self, project_dir):
        """In safe mode, commit requires precommit."""
        setup_gates_json(project_dir, mode="safe")

        stdin = make_hook_input("git commit -m 'test'")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0
        assert "block" in output

    def test_default_mode_no_push_requirements(self, project_dir):
        """In default mode, push has no requirements."""
        setup_gates_json(project_dir, mode="default")

        stdin = make_hook_input("git push origin main")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0
        assert output == ""

    def test_minimal_mode_no_commit_requirements(self, project_dir):
        """In minimal mode, commit has no requirements."""
        setup_gates_json(project_dir, mode="minimal")

        stdin = make_hook_input("git commit -m 'test'")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0
        assert output == ""

    def test_no_mode_field_treated_as_default(self, project_dir):
        """Missing mode field in gates.json behaves like default mode."""
        config = {
            "gate_mode": "legacy",
            "eval_threshold": 95,
        }
        (project_dir / "gates.json").write_text(json.dumps(config))
        write_gate_flag(project_dir, "precommit", "READY 2026-05-21")

        stdin = make_hook_input("git commit -m 'test'")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0
        assert output == ""
