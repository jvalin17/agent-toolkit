"""Direct tests for hooks/path_protection.py — G-SESSION-1, G-GATE-1, G-REPORT-1."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from path_protection import (  # noqa: E402
    GATE_WRITING_TOOLS,
    PROTECTED_PATHS,
    check_protected_paths,
)
from session_state import SessionState  # noqa: E402


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
