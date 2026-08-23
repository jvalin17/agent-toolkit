#!/usr/bin/env python3
"""Tests for roles/audit.py — session audit CLI."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "roles"))


class TestParseSession:
    def test_parses_tool_calls(self, tmp_path):
        from audit import parse_session

        log = tmp_path / "session.jsonl"
        log.write_text("\n".join([
            json.dumps({"message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}
            ]}}),
            json.dumps({"message": {"content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "foo.py"}}
            ]}}),
            json.dumps({"message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "git status"}}
            ]}}),
        ]))

        data = parse_session(log)
        assert data["tools"]["Bash"] == 2
        assert data["tools"]["Read"] == 1
        assert data["total_entries"] == 3

    def test_tracks_skill_invocations(self, tmp_path):
        from audit import parse_session

        log = tmp_path / "session.jsonl"
        log.write_text(json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "precommit"}}
        ]}}))

        data = parse_session(log)
        assert data["skills"] == ["precommit"]

    def test_tracks_agent_spawns(self, tmp_path):
        from audit import parse_session

        log = tmp_path / "session.jsonl"
        log.write_text(json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "Agent", "input": {"description": "Research patterns"}}
        ]}}))

        data = parse_session(log)
        assert data["agents"] == ["Research patterns"]

    def test_handles_empty_log(self, tmp_path):
        from audit import parse_session

        log = tmp_path / "session.jsonl"
        log.write_text("")

        data = parse_session(log)
        assert data["total_entries"] == 0
        assert data["tools"] == {}

    def test_handles_malformed_json(self, tmp_path):
        from audit import parse_session

        log = tmp_path / "session.jsonl"
        log.write_text("not json\n{bad json}\n")

        data = parse_session(log)
        assert data["total_entries"] == 2
        assert data["tools"] == {}


class TestFormatAudit:
    def test_formats_basic_audit(self):
        from audit import format_audit

        data = {
            "session_id": "test-123",
            "total_entries": 5,
            "tools": {"Bash": 3, "Read": 2},
            "skills": ["/precommit"],
            "agents": ["Research"],
            "role_mentions": {},
        }

        text = format_audit(data)
        assert "test-123" in text
        assert "Bash: 3" in text
        assert "/precommit" in text
        assert "Research" in text

    def test_formats_empty_session(self):
        from audit import format_audit

        data = {
            "session_id": "empty",
            "total_entries": 0,
            "tools": {},
            "skills": [],
            "agents": [],
            "role_mentions": {},
        }

        text = format_audit(data)
        assert "empty" in text
        assert "(none)" in text
