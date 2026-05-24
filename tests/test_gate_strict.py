"""Tests for strict mode gate enforcement in hooks/gate.py.

When mode=strict in gates.json, commit and push require both
precommit AND evaluate, regardless of the profile setting.
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
    """Build the stdin JSON that gate.py expects."""
    return json.dumps({"tool_input": {"command": command}})


def setup_gates_json(project_dir: Path, mode: str = "normal", profile: str = "minimal"):
    """Write a gates.json with given mode and profile."""
    config = {
        "gate_mode": "legacy",
        "enforcement": "block",
        "profile": profile,
        "mode": mode,
        "eval_threshold": 95,
        "profiles": {
            "minimal": {
                "commit_requires": ["precommit"],
                "push_requires": ["precommit"],
            },
            "standard": {
                "commit_requires": ["precommit"],
                "push_requires": ["precommit", "evaluate"],
            },
        },
    }
    (project_dir / "gates.json").write_text(json.dumps(config))


def write_gate_flag(project_dir: Path, skill: str, content: str):
    """Write a .gates/ flag file."""
    gates_dir = project_dir / ".gates"
    gates_dir.mkdir(exist_ok=True)
    (gates_dir / f"{skill}-passed").write_text(content)


class TestStrictModeGateEnforcement:
    def test_strict_mode_requires_evaluate_for_commit(self, project_dir):
        """In strict mode with minimal profile, commit still requires evaluate."""
        setup_gates_json(project_dir, mode="strict", profile="minimal")
        # Only precommit passed — no evaluate
        write_gate_flag(project_dir, "precommit", "READY 2026-05-21")

        stdin = make_hook_input("git commit -m 'test'")
        exit_code, output = run_gate(stdin, project_dir)

        # Should be blocked — evaluate missing
        assert exit_code == 0  # Blocking via JSON decision
        assert "block" in output
        assert "evaluate" in output.lower()

    def test_strict_mode_allows_commit_with_both(self, project_dir):
        """In strict mode, commit allowed when both precommit and evaluate pass."""
        setup_gates_json(project_dir, mode="strict", profile="minimal")
        write_gate_flag(project_dir, "precommit", "READY 2026-05-21")
        write_gate_flag(project_dir, "evaluate", "PASSED 96%")

        stdin = make_hook_input("git commit -m 'test'")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0

    def test_strict_mode_requires_evaluate_for_push(self, project_dir):
        """In strict mode, push also requires evaluate."""
        setup_gates_json(project_dir, mode="strict", profile="minimal")
        write_gate_flag(project_dir, "precommit", "READY 2026-05-21")

        stdin = make_hook_input("git push origin main")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0  # Blocking via JSON decision
        assert "block" in output
        assert "evaluate" in output.lower()

    def test_normal_mode_minimal_does_not_require_evaluate(self, project_dir):
        """In normal mode with minimal profile, commit only needs precommit."""
        setup_gates_json(project_dir, mode="normal", profile="minimal")
        write_gate_flag(project_dir, "precommit", "READY 2026-05-21")

        stdin = make_hook_input("git commit -m 'test'")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0

    def test_strict_mode_evaluate_below_threshold_blocked(self, project_dir):
        """Evaluate score below threshold still blocks in strict mode."""
        setup_gates_json(project_dir, mode="strict", profile="minimal")
        write_gate_flag(project_dir, "precommit", "READY 2026-05-21")
        write_gate_flag(project_dir, "evaluate", "PASSED 80%")  # Below 95

        stdin = make_hook_input("git commit -m 'test'")
        exit_code, output = run_gate(stdin, project_dir)

        assert exit_code == 0  # Blocking via JSON decision
        assert "block" in output
        assert "80" in output or "below" in output.lower()

    def test_no_mode_field_treated_as_normal(self, project_dir):
        """Missing mode field in gates.json behaves like normal mode."""
        config = {
            "gate_mode": "legacy",
            "enforcement": "block",
            "profile": "minimal",
            "eval_threshold": 95,
            "profiles": {
                "minimal": {
                    "commit_requires": ["precommit"],
                    "push_requires": ["precommit"],
                },
            },
        }
        (project_dir / "gates.json").write_text(json.dumps(config))
        write_gate_flag(project_dir, "precommit", "READY 2026-05-21")

        stdin = make_hook_input("git commit -m 'test'")
        exit_code, output = run_gate(stdin, project_dir)

        # Normal mode minimal — precommit is enough
        assert exit_code == 0
