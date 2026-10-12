"""hook_io — detect + normalize stdin; host-aware block responses."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

import pytest

from hook_io import (
    context_json,
    make_block_json,
    make_context_json,
    parse_hook_stdin,
    read_hook_event,
    run_guarded,
)


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


@pytest.mark.parametrize("stdin_text", ["", "   ", "{not json", '"a string"', "[1, 2]", "42", "null"])
def test_read_hook_event_malformed(stdin_text):
    assert read_hook_event(stdin_text) == {}


def test_read_hook_event_default_distinguishes_invalid_from_empty_object():
    assert read_hook_event("{not json", default=None) is None
    assert read_hook_event("{}", default=None) == {}


def test_read_hook_event_object():
    event = read_hook_event('{"tool_name": "Edit", "tool_input": {"file_path": "src/billing.py"}}')
    assert event["tool_name"] == "Edit"
    assert event["tool_input"]["file_path"] == "src/billing.py"


def test_read_hook_event_unicode_prompt():
    event = read_hook_event(json.dumps({"prompt": "Añade facturación — étape 1 ✓"}, ensure_ascii=False))
    assert event["prompt"] == "Añade facturación — étape 1 ✓"


def test_parse_hook_stdin_non_object_is_unknown():
    agent, canonical = parse_hook_stdin("[1, 2, 3]")
    assert agent == "unknown"
    assert canonical["tool_name"] == ""


def test_run_guarded_blocks_on_exception(capsys):
    """A crashing gate hook must deny the tool call, not exit 1 (which Claude Code ignores)."""
    def boom() -> int:
        raise KeyError("tool_input")

    code = run_guarded(boom, "gate_hook")
    out = capsys.readouterr()
    body = json.loads(out.out.strip().splitlines()[-1])
    assert code == 2
    assert body["decision"] == "block"
    assert "gate_hook" in body["reason"]
    assert "KeyError" in body["reason"]
    assert body["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_run_guarded_passes_through_normal_exit(capsys):
    assert run_guarded(lambda: 0, "gate_hook") == 0
    assert run_guarded(lambda: 2, "gate_hook") == 2
    assert capsys.readouterr().out == ""


def test_context_json_shape():
    body = json.loads(context_json("tests first", event="PostToolUse"))
    assert body == {
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "tests first"}
    }
