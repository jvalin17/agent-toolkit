"""Tests for hooks/gate_hook.py — commit/push gate enforcement.

Covers: command detection, flag validation, mode-based gates, signed mode.
"""

import json
import os
from pathlib import Path

import pytest

from gate.flags import sign_flag_file
from hooks.gate_hook import (
    detect_git_action,
    check_gate_flags,
    get_config_value,
    load_gate_config,
    run_gate,
)


@pytest.fixture
def project_dir(tmp_path):
    """Create a temp project directory with default gates.json."""
    gates = {
        "gate_mode": "legacy",
        "mode": "default",
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
        sign_flag_file(gates_dir / "precommit-passed", "READY 2026-05-20")
        missing = check_gate_flags(["precommit"], project_dir)
        assert missing == []

    def test_precommit_without_ready(self, project_dir, gates_dir):
        sign_flag_file(gates_dir / "precommit-passed", "")
        missing = check_gate_flags(["precommit"], project_dir)
        assert len(missing) == 1
        assert "READY" in missing[0] or "precommit" in missing[0]

    def test_evaluate_below_threshold(self, project_dir, gates_dir):
        sign_flag_file(gates_dir / "evaluate-passed", "PASSED 40% 2026-05-20")
        missing = check_gate_flags(["evaluate"], project_dir, eval_threshold=95)
        assert len(missing) == 1

    def test_evaluate_at_threshold(self, project_dir, gates_dir):
        sign_flag_file(gates_dir / "evaluate-passed", "PASSED 95% 2026-05-20")
        missing = check_gate_flags(["evaluate"], project_dir, eval_threshold=95)
        assert missing == []

    def test_evaluate_below_94(self, project_dir, gates_dir):
        sign_flag_file(gates_dir / "evaluate-passed", "PASSED 94% 2026-05-20")
        missing = check_gate_flags(["evaluate"], project_dir, eval_threshold=95)
        assert len(missing) == 1

    def test_reviewer_without_passed(self, project_dir, gates_dir):
        sign_flag_file(gates_dir / "reviewer-passed", "")
        missing = check_gate_flags(["reviewer"], project_dir)
        assert len(missing) == 1

    def test_reviewer_with_passed(self, project_dir, gates_dir):
        sign_flag_file(gates_dir / "reviewer-passed", "PASSED 2026-05-20")
        missing = check_gate_flags(["reviewer"], project_dir)
        assert missing == []


# --- Config loading ---


class TestLoadGateConfig:
    def test_loads_from_project_root(self, project_dir):
        config = load_gate_config(project_dir)
        assert config["gate_mode"] == "legacy"

    def test_returns_defaults_when_no_config(self, tmp_path):
        config = load_gate_config(tmp_path)
        assert config["enforcement"] == "block"
        assert config["gate_mode"] == "legacy"

    def test_loader_matches_gate_core(self, tmp_path):
        """hooks/gates.json is the last candidate for both the hook and gate.config."""
        from gate.config import find_gates_config

        (tmp_path / "hooks").mkdir()
        (tmp_path / "hooks" / "gates.json").write_text('{"gate_mode": "legacy", "mode": "tdd"}')
        assert find_gates_config(tmp_path) == tmp_path / "hooks" / "gates.json"
        assert load_gate_config(tmp_path)["mode"] == "tdd"

    @pytest.mark.parametrize("content", ["{not json", "", "   \n", "[1, 2]"])
    def test_corrupt_config_fails_closed(self, tmp_path, content):
        (tmp_path / "gates.json").write_text(content)
        config = load_gate_config(tmp_path)
        assert config["mode"] == "safe"
        assert "gates.json" in config["_config_error"]
        assert "_no_config" not in config


class TestMissingConfigFailsClosed:
    """No gates.json is fine for a plain repo, not for a repo that had one."""

    COMMIT = '{"tool_name":"Bash","tool_input":{"command":"git commit -m \\"add invoice export\\""}}'

    def _git(self, cwd, *args):
        import subprocess
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)

    def test_plain_repo_without_config_is_allowed(self, tmp_path):
        exit_code, output = run_gate(self.COMMIT, tmp_path)
        assert (exit_code, output) == (0, "")

    def test_deleted_gates_json_blocks(self, tmp_path):
        self._git(tmp_path, "init", "-q")
        self._git(tmp_path, "config", "user.email", "ana@acme.dev")
        self._git(tmp_path, "config", "user.name", "Ana")
        (tmp_path / "gates.json").write_text('{"gate_mode":"legacy","mode":"default"}')
        self._git(tmp_path, "add", "gates.json")
        self._git(tmp_path, "commit", "-q", "-m", "add gates")
        (tmp_path / "gates.json").unlink()

        _, output = run_gate(self.COMMIT, tmp_path)
        data = json.loads(output)
        assert data["decision"] == "block"
        assert "gates.json" in data["reason"]
        assert "deleted" in data["reason"] or "missing" in data["reason"]

    def test_toolkit_marker_without_config_blocks(self, tmp_path):
        (tmp_path / ".agent-toolkit").mkdir()
        _, output = run_gate(self.COMMIT, tmp_path)
        data = json.loads(output)
        assert data["decision"] == "block"
        assert ".agent-toolkit" in data["reason"]


class TestMultipleActions:
    def test_commit_and_push_in_one_command_checks_both_gates(self, project_dir, gates_dir):
        """Safe mode: precommit present but reviewer missing → the push half blocks."""
        (project_dir / "gates.json").write_text(json.dumps({"gate_mode": "legacy", "mode": "safe"}))
        sign_flag_file(gates_dir / "precommit-passed", "READY 2026-10-12")
        event = '{"tool_name":"Bash","tool_input":{"command":"git commit -m x && git push origin main"}}'
        _, output = run_gate(event, project_dir)
        data = json.loads(output)
        assert data["decision"] == "block"
        assert "push" in data["reason"]
        assert "reviewer" in data["reason"]

    def test_wrapped_commit_is_gated(self, project_dir):
        event = '{"tool_name":"Bash","tool_input":{"command":"bash -c \\"git commit -m x\\""}}'
        _, output = run_gate(event, project_dir)
        assert json.loads(output)["decision"] == "block"

    def test_unsigned_flag_does_not_unlock(self, project_dir, gates_dir):
        (gates_dir / "precommit-passed").write_text("READY 2026-10-12\n")
        _, output = run_gate(self_commit(), project_dir)
        data = json.loads(output)
        assert data["decision"] == "block"
        assert "unverified" in data["reason"]
        assert "unsigned" in data["reason"]


class TestSignedVerifyPath:
    def test_signed_verify_uses_toolkit_script(self, project_dir, monkeypatch):
        """A project copy of verify_gate.py (agent-editable) must never be the verifier."""
        from unittest.mock import patch
        import hooks.gate_hook as gh

        (project_dir / "gates.json").write_text(json.dumps({"gate_mode": "signed", "mode": "default"}))
        evil = project_dir / ".agent-toolkit" / "gate" / "scripts"
        evil.mkdir(parents=True)
        (evil / "verify_gate.py").write_text("import sys; sys.exit(0)\n")
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)

            class R:
                returncode = 0
                stdout = "abc123\n"
                stderr = ""
            return R()

        with patch.object(gh.subprocess, "run", side_effect=fake_run):
            exit_code, output = run_gate(self_commit(), project_dir)

        verify_calls = [c for c in calls if any("verify_gate.py" in str(a) for a in c)]
        assert len(verify_calls) == 1
        script = next(a for a in verify_calls[0] if str(a).endswith("verify_gate.py"))
        assert str(script).startswith(str(gh._TOOLKIT_ROOT))
        assert ".agent-toolkit" not in str(script)


def self_commit() -> str:
    return '{"tool_name":"Bash","tool_input":{"command":"git commit -m \\"x\\""}}'


class TestCorruptConfigBlocksGit:
    def _commit_event(self, message):
        return json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": f"git commit -m '{message}'"},
        })

    def test_corrupt_config_blocks_commit(self, tmp_path):
        (tmp_path / "gates.json").write_text("{not json")
        exit_code, output = run_gate(self._commit_event("add invoice export"), tmp_path)
        data = json.loads(output)
        assert data["decision"] == "block"
        assert "gates.json" in data["reason"]
        assert "invalid JSON" in data["reason"]

    def test_empty_config_file_blocks_push(self, tmp_path):
        (tmp_path / "gates.json").write_text("")
        event = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})
        _, output = run_gate(event, tmp_path)
        data = json.loads(output)
        assert data["decision"] == "block"
        assert "empty" in data["reason"]

    def test_unicode_commit_message(self, project_dir):
        """Default mode needs precommit; a non-ASCII message must not break the hook."""
        _, output = run_gate(self._commit_event("Añadir facturación — étape 1 ✓"), project_dir)
        data = json.loads(output)
        assert data["decision"] == "block"
        assert "precommit" in data["reason"]


# --- Full gate run (mode-based) ---


class TestRunGate:
    def test_commit_blocked_in_default_mode(self, project_dir):
        """Default mode requires precommit for commit."""
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0
        assert "block" in output

    def test_commit_allowed_with_precommit_in_default_mode(self, project_dir, gates_dir):
        sign_flag_file(gates_dir / "precommit-passed", "READY 2026-05-20")
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0
        assert output == ""

    def test_commit_allowed_in_minimal_mode(self, project_dir):
        """Minimal mode has no gates — commit always allowed."""
        (project_dir / "gates.json").write_text(json.dumps({
            "gate_mode": "legacy", "mode": "minimal",
        }))
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0
        assert output == ""

    def test_push_blocked_in_safe_mode_without_reviewer(self, project_dir, gates_dir):
        """Safe mode requires reviewer for push."""
        (project_dir / "gates.json").write_text(json.dumps({
            "gate_mode": "legacy", "mode": "safe",
        }))
        sign_flag_file(gates_dir / "precommit-passed", "READY 2026-05-20")
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git push origin main"}}',
            project_dir,
        )
        assert exit_code == 0
        assert "block" in output

    def test_push_allowed_in_safe_mode_with_reviewer(self, project_dir, gates_dir):
        """Safe mode allows push when reviewer passes."""
        (project_dir / "gates.json").write_text(json.dumps({
            "gate_mode": "legacy", "mode": "safe",
        }))
        sign_flag_file(gates_dir / "reviewer-passed", "PASSED 2026-05-20")
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git push origin main"}}',
            project_dir,
        )
        assert exit_code == 0
        assert output == ""

    def test_push_allowed_in_default_mode(self, project_dir):
        """Default mode has no push requirements."""
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git push origin main"}}',
            project_dir,
        )
        assert exit_code == 0
        assert output == ""

    def test_non_git_command_allowed(self, project_dir):
        exit_code, output = run_gate(
            '{"tool_input":{"command":"ls -la"}}',
            project_dir,
        )
        assert exit_code == 0

    def test_signed_mode_blocks_outside_git_repo(self, project_dir):
        """Signed mode always uses the toolkit verifier; with no repo it fails closed."""
        gates = {
            "gate_mode": "signed",
            "mode": "default",
        }
        (project_dir / "gates.json").write_text(json.dumps(gates))

        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0
        assert "block" in output
        assert "signed mode" in output

    def test_signed_mode_blocks_on_verify_oserror(
        self, project_dir, monkeypatch
    ):
        gates = {
            "gate_mode": "signed",
            "mode": "default",
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

    def test_env_mode_override_cannot_weaken(self, project_dir, monkeypatch):
        """AGENT_TOOLKIT_MODE=minimal is ignored when gates.json says default (still gated)."""
        monkeypatch.setenv("AGENT_TOOLKIT_MODE", "minimal")
        exit_code, output = run_gate(
            '{"tool_input":{"command":"git commit -m \\"test\\""}}',
            project_dir,
        )
        assert exit_code == 0
        assert json.loads(output)["decision"] == "block"

    def test_env_mode_override_can_strengthen(self, project_dir, gates_dir, monkeypatch):
        """AGENT_TOOLKIT_MODE=safe on a default project adds the reviewer push gate."""
        monkeypatch.setenv("AGENT_TOOLKIT_MODE", "safe")
        _, output = run_gate(
            '{"tool_input":{"command":"git push origin main"}}',
            project_dir,
        )
        assert "reviewer" in json.loads(output)["reason"]

    def test_protect_env_cannot_switch_off(self, monkeypatch):
        monkeypatch.setenv("AGENT_TOOLKIT_GATE_PROTECT", "false")
        monkeypatch.setenv("AGENT_TOOLKIT_EVAL_THRESHOLD", "10")
        monkeypatch.setenv("AGENT_TOOLKIT_SKILL_ENFORCE", "off")
        config = {"gate_protect": True, "eval_threshold": 95, "skill_enforce": "block"}
        assert get_config_value(config, "gate_protect", True) is True
        assert get_config_value(config, "eval_threshold", 95) == 95
        assert get_config_value(config, "skill_enforce", "remind") == "block"

    def test_protect_env_can_switch_on(self, monkeypatch):
        monkeypatch.setenv("AGENT_TOOLKIT_GATE_PROTECT", "true")
        monkeypatch.setenv("AGENT_TOOLKIT_EVAL_THRESHOLD", "99")
        config = {"gate_protect": False, "eval_threshold": 95}
        assert get_config_value(config, "gate_protect", True) is True
        assert get_config_value(config, "eval_threshold", 95) == 99


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


class TestStalePrecommitBlock:
    """Block commit if a code-change stamp is newer than precommit stamp."""

    def _make_stamp(self, gates_dir, skill, offset_seconds=0):
        from datetime import datetime, timezone, timedelta
        stamps_dir = gates_dir / "stamps"
        stamps_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
        (stamps_dir / skill).write_text(json.dumps({
            "skill": skill, "timestamp": ts.isoformat()
        }))

    def test_blocks_commit_when_impl_stamp_newer_than_precommit(self, project_dir, gates_dir):
        """Commit blocked when implementation stamp is newer than precommit."""
        sign_flag_file(gates_dir / "precommit-passed", "READY")
        self._make_stamp(gates_dir, "precommit", offset_seconds=0)
        self._make_stamp(gates_dir, "implementation", offset_seconds=1)
        (project_dir / "gates.json").write_text(json.dumps({"gate_mode": "legacy", "mode": "default"}))

        from hooks.gate_hook import run_gate
        _, output = run_gate(json.dumps({"tool_input": {"command": "git commit -m 'feat'"}}), project_dir)
        assert output != "", "should block when code-change stamp is newer than precommit"
        data = json.loads(output)
        assert data["decision"] == "block"

    def test_allows_commit_when_precommit_is_latest(self, project_dir, gates_dir):
        """Commit allowed when precommit stamp is the most recent."""
        sign_flag_file(gates_dir / "precommit-passed", "READY")
        self._make_stamp(gates_dir, "implementation", offset_seconds=0)
        self._make_stamp(gates_dir, "precommit", offset_seconds=1)
        (project_dir / "gates.json").write_text(json.dumps({"gate_mode": "legacy", "mode": "default"}))

        from hooks.gate_hook import run_gate
        _, output = run_gate(json.dumps({"tool_input": {"command": "git commit -m 'feat'"}}), project_dir)
        # Should pass — precommit is most recent
        if output:
            data = json.loads(output)
            assert data.get("decision") != "block"

    def test_skipped_in_minimal_mode(self, project_dir, gates_dir):
        """Minimal mode does not check stamp ordering."""
        (project_dir / "gates.json").write_text(json.dumps({"gate_mode": "legacy", "mode": "minimal"}))
        _, output = run_gate(json.dumps({"tool_input": {"command": "git commit -m 'feat'"}}), project_dir)
        assert output == "" or json.loads(output).get("decision") != "block"
