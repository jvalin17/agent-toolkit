"""Shared hook I/O — detect host, normalize stdin, emit host-aware responses.

All structural hooks should use this so Cursor/Grok/Codex/Windsurf payloads
are enforced the same way as Claude Code.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from agent_detect import detect_agent, detect_from_stdin
from stdin_adapter import normalize_input, normalize_output


_MISSING = object()


def read_hook_event(stdin_input: str, default: Any = _MISSING) -> Any:
    """Parse raw hook stdin into a dict.

    Empty, malformed, or non-object input returns `default` ({} when not
    given, so callers can `.get()` safely; pass `default=None` to tell a
    missing/invalid payload apart from a valid empty object).

    Every hook entry point should use this instead of calling json.loads on
    stdin itself, so malformed payloads are handled identically on every host.
    """
    fallback: Any = {} if default is _MISSING else default
    if not stdin_input or not isinstance(stdin_input, str) or not stdin_input.strip():
        return fallback
    try:
        raw = json.loads(stdin_input)
    except (json.JSONDecodeError, TypeError, ValueError):
        return fallback
    return raw if isinstance(raw, dict) else fallback


def context_json(message: str, event: str = "PreToolUse") -> str:
    """Claude Code additionalContext payload (host-agnostic hooks use make_context_json)."""
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": message,
        }
    })


def parse_hook_stdin(stdin_input: str) -> Tuple[str, Dict[str, Any]]:
    """Parse stdin JSON → (agent_id, canonical_event).

    Hook payloads identify the host — stdin signals win over env/filesystem
    so Cursor's CURSOR_* env does not mis-label Grok/Codex hook traffic.
    """
    empty = {
        "event": "",
        "tool_name": "",
        "command": "",
        "file_path": "",
        "prompt": "",
        "session_id": "",
        "raw": {},
    }
    raw = read_hook_event(stdin_input)
    if not raw:
        return "unknown", empty

    # Payload-first (critical for multi-host correctness)
    agent = detect_from_stdin(raw)
    if not agent:
        agent = detect_agent(raw)
    if agent == "unknown" or agent is None:
        if raw.get("hookEventName") or raw.get("toolInput"):
            agent = "grok-build"
        elif raw.get("hook_event_name") or raw.get("tool_input"):
            agent = "claude-code"
        elif raw.get("cursor_version"):
            agent = "cursor"
        elif raw.get("turn_id"):
            agent = "codex-cli"
        elif raw.get("trajectory_id") or raw.get("agent_action_name"):
            agent = "windsurf"
        else:
            agent = "claude-code"

    canonical = normalize_input(raw, agent)
    return agent, canonical


def make_block_json(reason: str, agent: str = "claude-code", event: str = "PreToolUse") -> str:
    """Host-aware deny payload. Always includes a hard block signal."""
    if agent == "windsurf":
        return normalize_output(event=event, message=reason, blocked=True, agent=agent)

    # Claude / Cursor / Codex / Grok — decision:block is the structural deny
    payload = {
        "decision": "block",
        "reason": reason,
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": reason,
            "permissionDecision": "deny",
        },
    }
    return json.dumps(payload)


def make_context_json(
    message: str,
    agent: str = "claude-code",
    event: str = "PreToolUse",
) -> str:
    """Non-blocking context injection."""
    return normalize_output(event=event, message=message, blocked=False, agent=agent)
