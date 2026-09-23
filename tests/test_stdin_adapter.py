"""Tests for hooks/stdin_adapter.py — normalize hook I/O across AI coding tools."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from stdin_adapter import normalize_input, normalize_output


# --- normalize_input ---


class TestNormalizeInput:
    """Normalize tool-specific stdin JSON into a canonical format."""

    def test_claude_code_pre_tool_use(self):
        raw = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "git status", "file_path": ""},
            "session_id": "abc",
            "transcript_path": "/home/.claude/projects/foo/s.jsonl",
        }
        result = normalize_input(raw, "claude-code")
        assert result["event"] == "PreToolUse"
        assert result["tool_name"] == "Bash"
        assert result["command"] == "git status"
        assert result["file_path"] == ""
        assert result["session_id"] == "abc"

    def test_claude_code_user_prompt(self):
        raw = {
            "hook_event_name": "UserPromptSubmit",
            "prompt": "build the feature",
            "session_id": "abc",
        }
        result = normalize_input(raw, "claude-code")
        assert result["event"] == "UserPromptSubmit"
        assert result["prompt"] == "build the feature"

    def test_cursor_pre_tool_use(self):
        raw = {
            "hook_event_name": "preToolUse",
            "tool_name": "Shell",
            "tool_input": {"command": "npm test"},
            "cursor_version": "1.7.3",
        }
        result = normalize_input(raw, "cursor")
        assert result["event"] == "PreToolUse"
        assert result["tool_name"] == "Bash"  # Shell → Bash
        assert result["command"] == "npm test"

    def test_cursor_before_submit(self):
        raw = {
            "hook_event_name": "beforeSubmitPrompt",
            "prompt": "fix the bug",
            "cursor_version": "1.7.3",
        }
        result = normalize_input(raw, "cursor")
        assert result["event"] == "UserPromptSubmit"
        assert result["prompt"] == "fix the bug"

    def test_codex_pre_tool_use(self):
        raw = {
            "hook_event_name": "PreToolUse",
            "tool_name": "shell",
            "tool_input": {"command": "pytest"},
            "turn_id": "t1",
            "session_id": "s1",
        }
        result = normalize_input(raw, "codex-cli")
        assert result["event"] == "PreToolUse"
        assert result["tool_name"] == "Bash"
        assert result["command"] == "pytest"

    def test_grok_pre_tool_use(self):
        raw = {
            "hookEventName": "PreToolUse",
            "toolName": "shell",
            "toolInput": {"command": "cargo test"},
            "sessionId": "g1",
        }
        result = normalize_input(raw, "grok-build")
        assert result["event"] == "PreToolUse"
        assert result["tool_name"] == "Bash"
        assert result["command"] == "cargo test"
        assert result["session_id"] == "g1"

    def test_windsurf_pre_run_command(self):
        raw = {
            "agent_action_name": "pre_run_command",
            "trajectory_id": "w1",
            "tool_info": {"command_line": "python test.py", "cwd": "/home"},
        }
        result = normalize_input(raw, "windsurf")
        assert result["event"] == "PreToolUse"
        assert result["tool_name"] == "Bash"
        assert result["command"] == "python test.py"

    def test_windsurf_pre_write_code(self):
        raw = {
            "agent_action_name": "pre_write_code",
            "trajectory_id": "w1",
            "tool_info": {"file_path": "/src/app.py"},
        }
        result = normalize_input(raw, "windsurf")
        assert result["event"] == "PreToolUse"
        assert result["tool_name"] == "Edit"
        assert result["file_path"] == "/src/app.py"

    def test_windsurf_pre_user_prompt(self):
        raw = {
            "agent_action_name": "pre_user_prompt",
            "trajectory_id": "w1",
            "tool_info": {"user_prompt": "add tests"},
        }
        result = normalize_input(raw, "windsurf")
        assert result["event"] == "UserPromptSubmit"
        assert result["prompt"] == "add tests"

    def test_unknown_tool_passes_through(self):
        raw = {"hook_event_name": "PreToolUse", "tool_name": "Bash"}
        result = normalize_input(raw, "unknown")
        assert result["event"] == "PreToolUse"
        assert result["tool_name"] == "Bash"

    def test_empty_input(self):
        result = normalize_input({}, "claude-code")
        assert result["event"] == ""
        assert result["tool_name"] == ""


# --- normalize_output ---


class TestNormalizeOutput:
    """Convert canonical response back to tool-specific format."""

    def test_claude_code_output(self):
        result = normalize_output(
            event="PreToolUse",
            message="blocked",
            blocked=True,
            agent="claude-code",
        )
        parsed = json.loads(result)
        assert parsed["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert "blocked" in parsed["hookSpecificOutput"]["additionalContext"]

    def test_cursor_output(self):
        result = normalize_output(
            event="PreToolUse",
            message="not allowed",
            blocked=True,
            agent="cursor",
        )
        parsed = json.loads(result)
        # Cursor uses same format as Claude Code for hook responses
        assert "additionalContext" in parsed["hookSpecificOutput"]

    def test_grok_output(self):
        result = normalize_output(
            event="PreToolUse",
            message="denied",
            blocked=True,
            agent="grok-build",
        )
        parsed = json.loads(result)
        assert "additionalContext" in parsed["hookSpecificOutput"]

    def test_windsurf_output(self):
        result = normalize_output(
            event="PreToolUse",
            message="proceed",
            blocked=False,
            agent="windsurf",
        )
        parsed = json.loads(result)
        assert "decision" in parsed
        assert parsed["decision"] == "allow"

    def test_windsurf_blocked(self):
        result = normalize_output(
            event="PreToolUse",
            message="not safe",
            blocked=True,
            agent="windsurf",
        )
        parsed = json.loads(result)
        assert parsed["decision"] == "deny"
        assert parsed["reason"] == "not safe"

    def test_non_blocking_returns_empty_for_claude(self):
        result = normalize_output(
            event="UserPromptSubmit",
            message="context here",
            blocked=False,
            agent="claude-code",
        )
        parsed = json.loads(result)
        assert parsed["hookSpecificOutput"]["additionalContext"] == "context here"
