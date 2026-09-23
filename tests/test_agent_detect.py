"""Tests for hooks/agent_detect.py — auto-detect which AI coding tool is running."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from agent_detect import (
    SUPPORTED_AGENTS,
    detect_from_env,
    detect_from_stdin,
    detect_from_filesystem,
    detect_agent,
)


# --- detect_from_env ---


class TestDetectFromEnv:
    def test_manual_override_takes_priority(self):
        with patch.dict(os.environ, {"AGENT_TOOLKIT_TOOL": "cursor", "CLAUDECODE": "1"}):
            assert detect_from_env() == "cursor"

    def test_claude_code(self):
        with patch.dict(os.environ, {"CLAUDECODE": "1"}, clear=True):
            assert detect_from_env() == "claude-code"

    def test_grok_build(self):
        with patch.dict(os.environ, {"GROK_SESSION_ID": "abc"}, clear=True):
            assert detect_from_env() == "grok-build"

    def test_codex_cli(self):
        with patch.dict(os.environ, {"CODEX_SANDBOX": "seatbelt"}, clear=True):
            assert detect_from_env() == "codex-cli"

    def test_cursor(self):
        with patch.dict(os.environ, {"CURSOR_CLI": "/usr/bin/cursor"}, clear=True):
            assert detect_from_env() == "cursor"

    def test_no_match(self):
        with patch.dict(os.environ, {}, clear=True):
            assert detect_from_env() is None

    def test_invalid_override_ignored(self):
        with patch.dict(os.environ, {"AGENT_TOOLKIT_TOOL": "invalid-tool"}, clear=True):
            assert detect_from_env() is None


# --- detect_from_stdin ---


class TestDetectFromStdin:
    def test_cursor_version(self):
        payload = {"cursor_version": "1.7.3", "hook_event_name": "preToolUse"}
        assert detect_from_stdin(payload) == "cursor"

    def test_windsurf_trajectory(self):
        payload = {"trajectory_id": "abc123", "agent_action_name": "pre_run_command"}
        assert detect_from_stdin(payload) == "windsurf"

    def test_grok_camelcase(self):
        payload = {"hookEventName": "PreToolUse", "sessionId": "xyz"}
        assert detect_from_stdin(payload) == "grok-build"

    def test_codex_turn_id(self):
        payload = {"turn_id": "t123", "hook_event_name": "PreToolUse"}
        assert detect_from_stdin(payload) == "codex-cli"

    def test_claude_code_transcript(self):
        payload = {"transcript_path": "/home/user/.claude/projects/foo/session.jsonl"}
        assert detect_from_stdin(payload) == "claude-code"

    def test_claude_code_hook_event(self):
        payload = {"hook_event_name": "PreToolUse", "session_id": "abc"}
        assert detect_from_stdin(payload) == "claude-code"

    def test_empty_payload(self):
        assert detect_from_stdin({}) is None

    def test_none_payload(self):
        assert detect_from_stdin(None) is None


# --- detect_from_filesystem ---


class TestDetectFromFilesystem:
    def test_claude_dir(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        with patch("agent_detect.Path.home", return_value=tmp_path):
            assert detect_from_filesystem() == "claude-code"

    def test_grok_dir(self, tmp_path):
        (tmp_path / ".grok").mkdir()
        with patch("agent_detect.Path.home", return_value=tmp_path):
            assert detect_from_filesystem() == "grok-build"

    def test_codex_dir(self, tmp_path):
        (tmp_path / ".codex").mkdir()
        with patch("agent_detect.Path.home", return_value=tmp_path):
            assert detect_from_filesystem() == "codex-cli"

    def test_cursor_dir(self, tmp_path):
        (tmp_path / ".cursor").mkdir()
        with patch("agent_detect.Path.home", return_value=tmp_path):
            assert detect_from_filesystem() == "cursor"

    def test_windsurf_dir(self, tmp_path):
        (tmp_path / ".windsurf").mkdir()
        with patch("agent_detect.Path.home", return_value=tmp_path):
            assert detect_from_filesystem() == "windsurf"

    def test_devin_dir(self, tmp_path):
        (tmp_path / ".devin").mkdir()
        with patch("agent_detect.Path.home", return_value=tmp_path):
            assert detect_from_filesystem() == "windsurf"

    def test_no_dirs(self, tmp_path):
        with patch("agent_detect.Path.home", return_value=tmp_path):
            assert detect_from_filesystem() is None

    def test_multiple_dirs_returns_first_match(self, tmp_path):
        # Claude comes first in priority
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".cursor").mkdir()
        with patch("agent_detect.Path.home", return_value=tmp_path):
            assert detect_from_filesystem() == "claude-code"


# --- detect_agent (integration) ---


class TestDetectAgent:
    def test_env_wins_over_stdin(self):
        with patch.dict(os.environ, {"CLAUDECODE": "1"}):
            result = detect_agent(stdin_payload={"cursor_version": "1.7"})
            assert result == "claude-code"

    def test_stdin_wins_over_filesystem(self, tmp_path):
        (tmp_path / ".cursor").mkdir()
        with patch.dict(os.environ, {}, clear=True), \
             patch("agent_detect.Path.home", return_value=tmp_path):
            result = detect_agent(stdin_payload={"trajectory_id": "abc"})
            assert result == "windsurf"

    def test_falls_through_to_filesystem(self, tmp_path):
        (tmp_path / ".grok").mkdir()
        with patch.dict(os.environ, {}, clear=True), \
             patch("agent_detect.Path.home", return_value=tmp_path):
            result = detect_agent(stdin_payload={})
            assert result == "grok-build"

    def test_returns_unknown_when_nothing_matches(self, tmp_path):
        with patch.dict(os.environ, {}, clear=True), \
             patch("agent_detect.Path.home", return_value=tmp_path):
            result = detect_agent(stdin_payload={})
            assert result == "unknown"

    def test_all_supported_agents_are_valid(self):
        for agent in SUPPORTED_AGENTS:
            assert isinstance(agent, str)
            assert len(agent) > 0
