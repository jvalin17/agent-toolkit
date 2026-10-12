"""hook_io — detect + normalize stdin; host-aware block responses."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from hook_io import parse_hook_stdin, make_block_json, make_context_json


def test_parse_cursor_shell_git_commit():
    raw = {
        "hook_event_name": "preToolUse",
        "tool_name": "Shell",
        "tool_input": {"command": "git commit -m 'x'"},
        "cursor_version": "1.7.3",
        "conversation_id": "c1",
    }
    agent, canonical = parse_hook_stdin(json.dumps(raw))
    assert agent == "cursor"
    assert canonical["tool_name"] == "Bash"
    assert "git commit" in canonical["command"]
    assert canonical["event"] == "PreToolUse"


def test_parse_grok_camelcase():
    raw = {
        "hookEventName": "PreToolUse",
        "toolName": "Bash",
        "toolInput": {"command": "git commit -m 'x'"},
        "sessionId": "g1",
    }
    agent, canonical = parse_hook_stdin(json.dumps(raw))
    assert agent == "grok-build"
    assert "git commit" in canonical["command"]


def test_parse_codex_shell():
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "shell",
        "tool_input": {"command": "git push origin main"},
        "turn_id": "t1",
        "session_id": "s1",
    }
    agent, canonical = parse_hook_stdin(json.dumps(raw))
    assert agent == "codex-cli"
    assert canonical["tool_name"] == "Bash"
    assert "git push" in canonical["command"]


def test_make_block_json_includes_decision_for_cursor():
    body = json.loads(make_block_json("no precommit", agent="cursor"))
    assert body.get("decision") == "block"
    assert "no precommit" in body.get("reason", "")


def test_make_block_json_windsurf_deny():
    body = json.loads(make_block_json("denied", agent="windsurf"))
    assert body.get("decision") == "deny"


def test_make_context_json_non_blocking():
    body = json.loads(make_context_json("hello", agent="claude-code", event="UserPromptSubmit"))
    assert body["hookSpecificOutput"]["additionalContext"] == "hello"
