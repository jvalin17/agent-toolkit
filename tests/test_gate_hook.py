"""Tests for hooks/gate_hook.py — commit/push gate enforcement.

Ports gate.sh bash tests to pytest. Covers: command detection, enforcement
modes, flag validation, profile-based gates, override chain, auto-escalation.
"""

import json
import os
from pathlib import Path

import pytest

from hooks.gate_hook import (
    detect_git_action,
    check_gate_flags,
    get_config_value,
    load_gate_config,
    resolve_enforcement,
    run_gate,
)


@pytest.fixture
def project_dir(tmp_path):
    """Create a temp project directory with default gates.json."""
    gates = {
        "gate_mode": "legacy",
        "enforcement": "block",
        "commit_requires": ["precommit"],
        "push_requires": ["evaluate"],
    }
    (tmp_path / "gates.json").write_text(json.dumps(gates))
    os.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def gates_dir(project_dir):
    """Create .gates/ directory."""
    d = project_dir / ".gates"
    d.mkdir(exist_ok=True)
    return d


# --- Command detection ---


class TestDetectGitAction:
    def test_simple_commit(self):
        assert detect_git_action('git commit -m "test"') == "commit"

    def test_simple_push(self):
        assert detect_git_action("git push origin main") == "push"

    def test_commit_and_push(self):
        """Push takes priority when both present."""
        assert detect_git_action('git commit -m "x" && git push origin main') == "push"

    def test_semicolon_separated(self):
        assert detect_git_action('git commit -m "x"; git push origin main') == "push"

    def test_non_git_command(self):
        assert detect_git_action("ls -la") is None

    def test_git_status(self):
        assert detect_git_action("git status") is None

    def test_git_with_c_flag_push(self):
        assert detect_git_action("git -C /tmp/repo push origin main") == "push"

    def test_commit_message_mentions_push(self):
        """git push inside a commit message should NOT trigger push gates."""
        assert detect_git_action('git commit -m "docs: how to git push safely"') == "commit"

    def test_empty_command(self):
        assert detect_git_action("") is None


# --- Flag validation ---


class TestCheckGateFlags:
    def test_missing_precommit(self, project_dir, gates_dir):
        missing = check_gate_flags(["precommit"], project_dir)
        assert "precommit" in missing

    def test_valid_precommit(self, project_dir, gates_dir):
        (gates_dir / "precommit-passed").write_text("READY 2026-05-20")
        missing = check_gate_flags(["precommit"], project_dir)
        assert missing == []

    def test_precommit_without_ready(self, project_dir, gates_dir):
        (gates_dir / "precommit-passed").write_text("")
        missing = check_gate_flags(["precommit"], project_dir)
        assert len(missing) == 1
        assert "READY" in missing[0] or "precommit" in missing[0]

    def test_evaluate_below_threshold(self, project_dir, gates_dir):
        (gates_dir / "evaluate-passed").write_text("PASSED 40% 2026-05-20")
        missing = check_gate_flags(["evaluate"], project_dir, eval_threshold=95)
        assert len(missing) == 1

    def test_evaluate_at_threshold(self, project_dir, gates_dir):
        (gates_dir / "evaluate-passed").write_text("PASSED 95% 2026-05-20")
        missing = check_gate_flags(["evaluate"], project_dir, eval_threshold=95)
        assert missing == []

    def test_evaluate_below_94(self, project_dir, gates_dir):
        (gates_dir / "evaluate-passed").write_text("PASSED 94% 2026-05-20")
        missing = check_gate_flags(["evaluate"], project_dir, eval_threshold=95)
        assert len(missing) == 1

    def test_reviewer_without_passed(self, project_dir, gates_dir):
        (gates_dir / "reviewer-passed").write_text("")
        missing = check_gate_flags(["reviewer"], project_dir)
        assert len(missing) == 1

    def test_reviewer_with_passed(self, project_dir, gates_dir):
        (gates_dir / "reviewer-passed").write_text("PASSED 2026-05-20")
        missing = check_gate_flags(["reviewer"], project_dir)
        assert missing == []


# --- Config loading ---


class TestLoadGateConfig:
    def test_loads_from_project_root(self, project_dir):
        config = load_gate_config(project_dir)
        assert config["gate_mode"] == "legacy"
        assert config["enforcement"] == "block"

    def test_returns_defaults_when_no_config(self, tmp_path):
        config = load_gate_config(tmp_path)
        assert config["enforcement"] == "block"
        assert config["gate_mode"] == "legacy"


# --- Enforcement override chain ---


class TestResolveEnforcement:
    def test_default_from_config(self, project_dir):
        result = resolve_enforcement("block", project_dir, env_override=None)
        assert result == "block"

    def test_file_override(self, project_dir, gates_dir):
        (gates_dir / "enforcement-override").write_text("warn")
        result = resolve_enforcement("block", project_dir, env_override=None)
        assert result == "warn"

    def test_env_var_overrides_file(self, project_dir, gates_dir):
        (gates_dir / "enforcement-override").write_text("warn")
        result = resolve_enforcement("block", project_dir, env_override="block")
        assert result == "block"

    def test_env_var_overrides_config(self, project_dir):
        result = resolve_enforcement("warn", project_dir, env_override="block")
        assert result == "block"


# --- Full gate run ---


class TestRunGate:
    def test_commit_blocked_without_precommit(self, project_dir):
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0  # Blocking via JSON decision, not exit code
        assert "block" in output
        assert "BLOCKED" in output

    def test_commit_allowed_with_precommit(self, project_dir, gates_dir):
        (gates_dir / "precommit-passed").write_text("READY 2026-05-20")
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0

    def test_push_blocked_without_evaluate(self, project_dir, gates_dir):
        (gates_dir / "precommit-passed").write_text("READY 2026-05-20")
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git push origin main"}}',
            project_dir,
        )
        assert exit_code == 0  # Blocking via JSON decision
        assert "block" in output

    def test_push_allowed_with_all_flags(self, project_dir, gates_dir):
        (gates_dir / "precommit-passed").write_text("READY 2026-05-20")
        (gates_dir / "evaluate-passed").write_text("PASSED 96% 2026-05-20")
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git push origin main"}}',
            project_dir,
        )
        assert exit_code == 0

    def test_non_git_command_allowed(self, project_dir):
        exit_code, output = run_gate(
            '{"tool_input":{"command":"ls -la"}}',
            project_dir,
        )
        assert exit_code == 0

    def test_warn_mode_exits_zero_with_warning(self, project_dir):
        # Switch to warn mode
        gates = json.loads((project_dir / "gates.json").read_text())
        gates["enforcement"] = "warn"
        (project_dir / "gates.json").write_text(json.dumps(gates))

        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0
        assert "GATE WARNING" in output

    def test_auto_escalation_on_warn(self, project_dir):
        """First warn violation writes .gates/enforcement-override=block."""
        gates = json.loads((project_dir / "gates.json").read_text())
        gates["enforcement"] = "warn"
        (project_dir / "gates.json").write_text(json.dumps(gates))

        run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        override_file = project_dir / ".gates" / "enforcement-override"
        assert override_file.exists()
        assert override_file.read_text().strip() == "block"

    def test_second_commit_blocked_after_escalation(self, project_dir):
        """After auto-escalation, next commit is hard-blocked."""
        gates = json.loads((project_dir / "gates.json").read_text())
        gates["enforcement"] = "warn"
        (project_dir / "gates.json").write_text(json.dumps(gates))

        # First violation → escalates
        run_gate(
            '{"tool_input":{"command":"git commit -m \\"first\\""}}',
            project_dir,
        )
        # Second attempt → blocked
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"second\\""}}',
            project_dir,
        )
        assert exit_code == 0  # Blocking via JSON decision, not exit code
        assert "block" in output
        assert "BLOCKED" in output

    def test_env_var_enforcement_override(self, project_dir):
        """AGENT_TOOLKIT_ENFORCEMENT env var overrides gates.json."""
        gates = json.loads((project_dir / "gates.json").read_text())
        gates["enforcement"] = "warn"
        (project_dir / "gates.json").write_text(json.dumps(gates))

        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
            env_enforcement="block",
        )
        assert exit_code == 0  # Blocking via JSON decision
        assert "block" in output

    def test_profile_based_gates(self, project_dir, gates_dir):
        """Profile-based config resolves correct requirements."""
        gates = {
            "gate_mode": "legacy",
            "enforcement": "block",
            "profile": "strict",
            "profiles": {
                "strict": {
                    "commit_requires": ["precommit", "evaluate"],
                    "push_requires": ["evaluate", "reviewer"],
                }
            },
        }
        (project_dir / "gates.json").write_text(json.dumps(gates))
        (gates_dir / "precommit-passed").write_text("READY 2026-05-20")

        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0  # Blocking via JSON decision
        assert "block" in output  # Missing evaluate for strict commit

    def test_signed_mode_blocks_when_verify_script_missing(self, project_dir):
        gates = {
            "gate_mode": "signed",
            "enforcement": "block",
            "profile": "minimal",
        }
        (project_dir / "gates.json").write_text(json.dumps(gates))

        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0
        assert "block" in output
        assert "verify_gate.py not found" in output

    def test_signed_mode_blocks_on_verify_oserror(
        self, project_dir, monkeypatch
    ):
        gates = {
            "gate_mode": "signed",
            "enforcement": "block",
            "profile": "minimal",
        }
        (project_dir / "gates.json").write_text(json.dumps(gates))
        gate_dir = project_dir / ".agent-toolkit" / "gate" / "scripts"
        gate_dir.mkdir(parents=True)
        (gate_dir / "verify_gate.py").write_text("# stub\n")

        def boom(*args, **kwargs):
            raise OSError("python3 not found")

        monkeypatch.setattr("hooks.gate_hook.subprocess.run", boom)

        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0
        assert "block" in output
        assert "verification unavailable" in output


class TestGetConfigValue:
    """get_config_value reads from config dict with env var override."""

    def test_reads_from_config(self):
        config = {"tdd": True, "model": "opus"}
        assert get_config_value(config, "tdd", False) is True
        assert get_config_value(config, "model", "auto") == "opus"

    def test_returns_default_when_missing(self):
        config = {}
        assert get_config_value(config, "tdd", True) is True
        assert get_config_value(config, "max_session_minutes", 0) == 0
        assert get_config_value(config, "model", "auto") == "auto"

    def test_env_var_overrides_config(self, monkeypatch):
        config = {"tdd": True}
        monkeypatch.setenv("AGENT_TOOLKIT_TDD", "false")
        assert get_config_value(config, "tdd", True) is False

    def test_bool_coercion_from_env(self, monkeypatch):
        config = {}
        for truthy in ("true", "1", "yes"):
            monkeypatch.setenv("AGENT_TOOLKIT_AUTO", truthy)
            assert get_config_value(config, "auto", False) is True
        for falsy in ("false", "0", "no"):
            monkeypatch.setenv("AGENT_TOOLKIT_AUTO", falsy)
            assert get_config_value(config, "auto", False) is False

    def test_int_coercion_from_env(self, monkeypatch):
        config = {}
        monkeypatch.setenv("AGENT_TOOLKIT_MAX_SESSION_MINUTES", "30")
        assert get_config_value(config, "max_session_minutes", 0) == 30

    def test_string_passthrough_from_env(self, monkeypatch):
        config = {"model": "opus"}
        monkeypatch.setenv("AGENT_TOOLKIT_MODEL", "sonnet")
        assert get_config_value(config, "model", "auto") == "sonnet"
