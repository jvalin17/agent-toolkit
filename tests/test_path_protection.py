"""Direct tests for hooks/path_protection.py — G-SESSION-1, G-GATE-1, G-REPORT-1."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from path_protection import (
    GATE_WRITING_TOOLS,
    PROTECTED_PATHS,
    check_protected_paths,
)
from session_state import SessionState


def _state(gate_protect=True, report_protect=True):
    return SessionState(
        session_start=1760227200,  # 2025-10-12T00:00:00Z
        gate_protect=gate_protect,
        report_protect=report_protect,
    )


class TestProtectedDirs:
    @pytest.mark.parametrize("tool", ["Write", "Edit"])
    @pytest.mark.parametrize("path, rule", [
        ("/home/ana/app/.session/state.json", "G-SESSION-1"),
        ("/home/ana/app/.gates/precommit-passed", "G-GATE-1"),
        ("/home/ana/app/.gates/stamps/reviewer", "G-GATE-1"),
        ("/home/ana/app/reports/precommit/pc_login_1a2b3c4d.md", "G-REPORT-1"),
    ])
    def test_blocks_write_to_each_protected_dir(self, tool, path, rule):
        blocked, msg = check_protected_paths(_state(), tool, path, "")
        assert blocked is True
        expected = next(s["message"] for s in PROTECTED_PATHS if s["rule"] == rule)
        assert msg == expected

    def test_allows_write_to_source_file(self):
        blocked, msg = check_protected_paths(
            _state(), "Write", "/home/ana/app/src/billing/invoice.py", ""
        )
        assert blocked is False
        assert msg == ""

    def test_allows_unicode_source_path(self):
        blocked, _ = check_protected_paths(
            _state(), "Edit", "/home/ana/app/src/módulos/façade.py", ""
        )
        assert blocked is False

    def test_bash_write_to_gates_blocked(self):
        blocked, _ = check_protected_paths(
            _state(), "Bash", "", "echo READY > .gates/precommit-passed"
        )
        assert blocked is True

    def test_bash_read_of_gates_allowed(self):
        blocked, _ = check_protected_paths(
            _state(), "Bash", "", "cat .gates/precommit-passed"
        )
        assert blocked is False

    def test_gate_protect_off_allows_gates_write(self):
        blocked, _ = check_protected_paths(
            _state(gate_protect=False), "Write", "/home/ana/app/.gates/precommit-passed", ""
        )
        assert blocked is False

    def test_report_protect_off_allows_reports_write(self):
        blocked, _ = check_protected_paths(
            _state(report_protect=False), "Write", "/home/ana/app/reports/evaluate/x.md", ""
        )
        assert blocked is False


class TestDefaultDeny:
    """Bash that names a protected path is denied unless every segment is read-only."""

    @pytest.mark.parametrize("command", [
        "touch .gates/precommit-passed",
        "python3 -c 'open(\".gates/precommit-passed\",\"w\").write(\"READY\")'",
        "ln -s /tmp/x .gates/evaluate-passed",
        "cp /tmp/flag .gates/precommit-passed",
        "node -e 'require(\"fs\").writeFileSync(\".gates/evaluate-passed\",\"PASSED 100\")'",
        "cat .gates/precommit-passed > /tmp/copy && touch .gates/reviewer-passed",
        "perl -e 'open(F,\">.session/state.json\")'",
        "truncate -s 0 reports/precommit/pc_login_1a2b3c4d.md",
        "dd if=/dev/zero of=.gates/x",
        "cat .gates/precommit-passed | tee .gates/evaluate-passed",
    ])
    def test_default_deny_for_protected_paths(self, command):
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command
        assert "hook-managed" in msg or "read-only" in msg

    @pytest.mark.parametrize("command", [
        "cat .gates/precommit-passed",
        "ls -la .gates/",
        "ls .gates/stamps 2>/dev/null",
        "grep -c READY .gates/precommit-passed",
        "head -n 3 reports/precommit/pc_login_1a2b3c4d.md",
        "stat .session/state.json",
        "git status --short .gates/",
        "git check-ignore -v .gates/precommit-passed",
        "find .gates -type f",
        "wc -l reports/evaluate/eval_login_1a2b3c4d.md",
        "test -f .gates/precommit-passed && cat .gates/precommit-passed",
    ])
    def test_read_only_access_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    def test_unparseable_command_naming_protected_path_is_denied(self):
        blocked, _ = check_protected_paths(_state(), "Bash", "", "cat '.gates/precommit-passed")
        assert blocked is True


class TestHeredocsAndGit:
    """Commit messages and file contents are data; interpreter heredocs are code."""

    def test_commit_message_heredoc_naming_policy_files_allowed(self):
        command = (
            "git commit -q -F - <<'EOF'\n"
            "Harden gates\n\n"
            "A deleted gates.json now blocks; .gates/ flags are signed; the .agent-toolkit\n"
            "verifier is never used; key lives outside signing.key paths.\n"
            "EOF\n"
            "git log --oneline -1 && git push origin main"
        )
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, msg

    def test_heredoc_after_a_chain_uses_only_its_own_command(self):
        command = (
            "python3 -m pytest -q && git add -A && git commit -q -F - <<'EOF'\n"
            "Fail closed when gates.json is deleted; sign .gates/ flags\n"
            "EOF\n"
            "git push origin main"
        )
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, msg

    def test_interpreter_heredoc_is_still_scanned(self):
        command = "bash <<'EOF'\ntouch .gates/precommit-passed\nEOF"
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True
        command = "python3 - <<'EOF'\nopen('.gates/precommit-passed','w')\nEOF"
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True

    def test_cat_heredoc_into_protected_path_blocked(self):
        command = "cat > .gates/precommit-passed <<'EOF'\nREADY\nEOF"
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True

    @pytest.mark.parametrize("command", [
        "git add gates.json",
        "git add -A && git commit -m 'tighten gates.json policy'",
        "git diff HEAD -- gates.json .claude/settings.json",
        "git push origin main",
    ])
    def test_git_non_writing_subcommands_allowed(self, command):
        blocked, msg = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, msg

    @pytest.mark.parametrize("command", [
        "git checkout -- gates.json",
        "git restore gates.json",
        "git rm gates.json",
        "git checkout HEAD~1 -- .claude/settings.json",
    ])
    def test_git_writing_subcommands_naming_policy_blocked(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command


class TestConfigFiles:
    """gates.json and host hook settings are policy — the agent may read, not write."""

    @pytest.mark.parametrize("path", [
        "/home/ana/app/gates.json",
        "gates.json",
        "/home/ana/app/.claude/settings.json",
        "/home/ana/app/.claude/settings.local.json",
        "/home/ana/.claude/settings.json",
        "/home/ana/app/.cursor/hooks.json",
        "/home/ana/app/.grok/hooks.json",
        "/home/ana/app/.windsurf/hooks.json",
        "/home/ana/app/.codex/config.toml",
        "/home/ana/app/.agent-toolkit/gate/scripts/verify_gate.py",
    ])
    @pytest.mark.parametrize("tool", ["Write", "Edit"])
    def test_config_files_protected(self, tool, path):
        blocked, msg = check_protected_paths(_state(), tool, path, "")
        assert blocked is True, path
        assert "G-CONFIG-1" in msg

    @pytest.mark.parametrize("path", [
        "/home/ana/agent-toolkit/templates/gates.json",
        "/home/ana/agent-toolkit/hooks/gates.json",
        "/home/ana/agent-toolkit/hooks/hooks.json",
        "/home/ana/app/src/settings.py",
        "/home/ana/app/docs/gates.md",
    ])
    def test_toolkit_sources_and_lookalikes_allowed(self, path):
        blocked, _ = check_protected_paths(_state(), "Write", path, "")
        assert blocked is False, path

    @pytest.mark.parametrize("command", [
        "jq '.mode = \"minimal\"' gates.json > gates.json.tmp && mv gates.json.tmp gates.json",
        "rm gates.json",
        "sed -i 's/safe/minimal/' gates.json",
        "python3 -c 'import json; json.dump({}, open(\"gates.json\",\"w\"))'",
        "cp /tmp/settings.json .claude/settings.json",
    ])
    def test_bash_writes_to_config_blocked(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command

    @pytest.mark.parametrize("command", ["cat gates.json", "jq .mode gates.json", "git diff gates.json"])
    def test_bash_reads_of_config_allowed(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is False, command

    def test_config_protection_follows_gate_protect(self):
        blocked, _ = check_protected_paths(_state(gate_protect=False), "Write", "/home/ana/app/gates.json", "")
        assert blocked is False


class TestSecretFiles:
    """Signing and flag keys must never reach the agent, not even through Read."""

    @pytest.mark.parametrize("path", [
        "/home/ana/app/.gate/signing.key",
        "/home/ana/app/.gate/private.pem",
        "/home/ana/.agent-toolkit/flag.key",
        "/home/ana/app/.session/state.json",
    ])
    def test_read_of_secret_files_blocked(self, path):
        blocked, msg = check_protected_paths(_state(), "Read", path, "")
        assert blocked is True, path
        assert "secret" in msg.lower() or "hook-managed" in msg

    @pytest.mark.parametrize("path", [
        "/home/ana/app/.gates/precommit-passed",
        "/home/ana/app/reports/precommit/pc_login_1a2b3c4d.md",
        "/home/ana/app/.gate/signing.meta.json",
        "/home/ana/app/src/billing/invoice.py",
    ])
    def test_read_of_non_secret_files_allowed(self, path):
        blocked, _ = check_protected_paths(_state(), "Read", path, "")
        assert blocked is False, path

    @pytest.mark.parametrize("command", [
        "cat .gate/signing.key",
        "python3 -c 'print(open(\".gate/signing.key\").read())'",
        "cat ~/.agent-toolkit/flag.key",
        "base64 /home/ana/.agent-toolkit/flag.key",
        "cp .gate/signing.key /tmp/k",
    ])
    def test_bash_access_to_secret_files_blocked(self, command):
        blocked, _ = check_protected_paths(_state(), "Bash", "", command)
        assert blocked is True, command

    @pytest.mark.parametrize("tool", ["Write", "Edit"])
    def test_write_to_key_dir_blocked(self, tool):
        blocked, _ = check_protected_paths(_state(), tool, "/home/ana/app/.gate/gate-token.jwt", "")
        assert blocked is True


class TestGateWritingTools:
    """stamp_skill is a forgery on hook-stamping hosts and the real path elsewhere."""

    STAMP_TOOL = "mcp__agent-toolkit__stamp_skill"

    def test_registry_names_stamp_tool(self):
        assert self.STAMP_TOOL in GATE_WRITING_TOOLS

    @pytest.mark.parametrize("tool_name", [
        "mcp__agent-toolkit__stamp_skill",
        "mcp__agent_toolkit__stamp_skill",
    ])
    def test_blocks_mcp_stamp_tool(self, tool_name):
        blocked, msg = check_protected_paths(_state(), tool_name, "", "", agent="claude-code")
        assert blocked is True
        assert "stamp" in msg.lower()
        assert "G-GATE-1" in msg

    def test_detects_claude_code_from_environment(self, monkeypatch):
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.delenv("AGENT_TOOLKIT_TOOL", raising=False)
        blocked, _ = check_protected_paths(_state(), self.STAMP_TOOL, "", "")
        assert blocked is True

    @pytest.mark.parametrize("agent", ["cursor", "gemini", "codex-cli", "grok-build", "windsurf", "default"])
    def test_cli_stamp_hosts_may_call_stamp_tool(self, agent):
        """Cursor, Gemini, Codex, Grok, Windsurf have no Skill hook — cli stamps are legitimate."""
        blocked, _ = check_protected_paths(_state(), self.STAMP_TOOL, "", "", agent=agent)
        assert blocked is False

    def test_gate_protect_off_allows_mcp_stamp_tool(self):
        blocked, _ = check_protected_paths(
            _state(gate_protect=False), self.STAMP_TOOL, "", "", agent="claude-code"
        )
        assert blocked is False

    def test_other_mcp_tools_allowed(self):
        blocked, _ = check_protected_paths(
            _state(), "mcp__agent-toolkit__get_skill", "", "", agent="claude-code"
        )
        assert blocked is False
