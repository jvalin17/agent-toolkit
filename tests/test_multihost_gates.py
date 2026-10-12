"""Foolproof gates: Cursor / Grok / Codex payloads must block commit without precommit."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from gate_hook import run_gate
sys.path.insert(0, str(ROOT))
from gate.flags import sign_flag_file


def _project_with_gates(tmp_path: Path) -> Path:
    (tmp_path / "gates.json").write_text(
        json.dumps({"mode": "default", "gate_mode": "legacy", "eval_threshold": 95})
    )
    return tmp_path


@pytest.mark.parametrize(
    "payload",
    [
        {
            "hook_event_name": "preToolUse",
            "tool_name": "Shell",
            "tool_input": {"command": "git commit -m 'x'"},
            "cursor_version": "1.7.3",
        },
        {
            "hookEventName": "PreToolUse",
            "toolName": "Bash",
            "toolInput": {"command": "git commit -m 'x'"},
            "sessionId": "g1",
        },
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "shell",
            "tool_input": {"command": "git commit -m 'fix'"},
            "turn_id": "t1",
            "session_id": "s1",
        },
    ],
    ids=["cursor", "grok", "codex"],
)
def test_commit_blocked_without_precommit(tmp_path, payload):
    project = _project_with_gates(tmp_path)
    code, output = run_gate(json.dumps(payload), project)
    assert output, "expected block JSON"
    body = json.loads(output)
    assert body.get("decision") in ("block", "deny")
    assert "precommit" in body.get("reason", "").lower() or "skills" in body.get("reason", "").lower()


def test_cursor_commit_allowed_with_precommit_flag(tmp_path):
    project = _project_with_gates(tmp_path)
    gates = project / ".gates"
    gates.mkdir()
    sign_flag_file(gates / "precommit-passed", "READY\n")
    payload = {
        "hook_event_name": "preToolUse",
        "tool_name": "Shell",
        "tool_input": {"command": "git commit -m 'ok'"},
        "cursor_version": "1.7.3",
    }
    code, output = run_gate(json.dumps(payload), project)
    # default mode requires only precommit for commit
    assert code == 0
    if output:
        body = json.loads(output)
        assert body.get("decision") != "block"
