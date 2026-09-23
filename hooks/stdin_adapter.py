"""Normalize hook stdin/stdout across AI coding tools.

Each tool sends different JSON schemas for the same concepts. This adapter
converts tool-specific input into a canonical format that all hooks can use,
and converts canonical responses back to tool-specific output.

Canonical input format:
    event: str        — PascalCase event name (PreToolUse, PostToolUse, UserPromptSubmit)
    tool_name: str    — Canonical tool name (Bash, Edit, Write, Read, Agent, Skill)
    command: str      — Shell command (for Bash tools)
    file_path: str    — File path (for Edit/Write/Read tools)
    prompt: str       — User prompt (for UserPromptSubmit)
    session_id: str   — Session identifier
    raw: dict         — Original payload preserved for tool-specific access
"""

import json
from typing import Any, Dict, Optional


# --- Tool name normalization ---

# Map tool-specific tool names to canonical names
_TOOL_NAME_MAP = {
    # Cursor
    "Shell": "Bash",
    "TabWrite": "Edit",
    # Codex CLI
    "shell": "Bash",
    "apply_patch": "Edit",
    "file_write": "Write",
    "file_read": "Read",
    # Grok Build
    # (mostly PascalCase like Claude Code, just shell differs)
}

# Map tool-specific event names to canonical PascalCase
_EVENT_NAME_MAP = {
    # Cursor (camelCase)
    "preToolUse": "PreToolUse",
    "postToolUse": "PostToolUse",
    "beforeSubmitPrompt": "UserPromptSubmit",
    "afterFileEdit": "PostToolUse",
    "beforeShellExecution": "PreToolUse",
    "afterShellExecution": "PostToolUse",
    "sessionStart": "SessionStart",
    "stop": "Stop",
    # Windsurf (snake_case action names)
    "pre_run_command": "PreToolUse",
    "post_run_command": "PostToolUse",
    "pre_write_code": "PreToolUse",
    "post_write_code": "PostToolUse",
    "pre_read_code": "PreToolUse",
    "post_read_code": "PostToolUse",
    "pre_user_prompt": "UserPromptSubmit",
    "post_cascade_response": "Stop",
}

# Windsurf action → canonical tool name
_WINDSURF_TOOL_MAP = {
    "pre_run_command": "Bash",
    "post_run_command": "Bash",
    "pre_write_code": "Edit",
    "post_write_code": "Edit",
    "pre_read_code": "Read",
    "post_read_code": "Read",
    "pre_mcp_tool_use": "MCP",
    "post_mcp_tool_use": "MCP",
}


def _normalize_tool_name(name: str) -> str:
    """Convert tool-specific tool name to canonical."""
    return _TOOL_NAME_MAP.get(name, name)


def _normalize_event(name: str) -> str:
    """Convert tool-specific event name to canonical PascalCase."""
    return _EVENT_NAME_MAP.get(name, name)


# --- Input normalization ---


def _normalize_claude_code(raw: dict) -> dict:
    """Normalize Claude Code stdin JSON."""
    tool_input = raw.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    return {
        "event": raw.get("hook_event_name", ""),
        "tool_name": raw.get("tool_name", ""),
        "command": tool_input.get("command", ""),
        "file_path": tool_input.get("file_path", ""),
        "prompt": raw.get("prompt", ""),
        "session_id": raw.get("session_id", ""),
        "raw": raw,
    }


def _normalize_cursor(raw: dict) -> dict:
    """Normalize Cursor stdin JSON."""
    event = _normalize_event(raw.get("hook_event_name", ""))
    tool_name = _normalize_tool_name(raw.get("tool_name", ""))
    tool_input = raw.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    return {
        "event": event,
        "tool_name": tool_name,
        "command": tool_input.get("command", ""),
        "file_path": tool_input.get("file_path", ""),
        "prompt": raw.get("prompt", ""),
        "session_id": raw.get("conversation_id", ""),
        "raw": raw,
    }


def _normalize_codex(raw: dict) -> dict:
    """Normalize Codex CLI stdin JSON."""
    tool_input = raw.get("tool_input", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    return {
        "event": raw.get("hook_event_name", ""),
        "tool_name": _normalize_tool_name(raw.get("tool_name", "")),
        "command": tool_input.get("command", ""),
        "file_path": tool_input.get("file_path", ""),
        "prompt": raw.get("prompt", ""),
        "session_id": raw.get("session_id", ""),
        "raw": raw,
    }


def _normalize_grok(raw: dict) -> dict:
    """Normalize Grok Build stdin JSON (camelCase fields)."""
    tool_input = raw.get("toolInput", {})
    if not isinstance(tool_input, dict):
        tool_input = {}

    return {
        "event": raw.get("hookEventName", ""),
        "tool_name": _normalize_tool_name(raw.get("toolName", "")),
        "command": tool_input.get("command", ""),
        "file_path": tool_input.get("file_path", tool_input.get("filePath", "")),
        "prompt": raw.get("prompt", ""),
        "session_id": raw.get("sessionId", ""),
        "raw": raw,
    }


def _normalize_windsurf(raw: dict) -> dict:
    """Normalize Windsurf stdin JSON (agent_action_name + tool_info)."""
    action = raw.get("agent_action_name", "")
    tool_info = raw.get("tool_info", {})
    if not isinstance(tool_info, dict):
        tool_info = {}

    event = _normalize_event(action)
    tool_name = _WINDSURF_TOOL_MAP.get(action, "")

    return {
        "event": event,
        "tool_name": tool_name,
        "command": tool_info.get("command_line", ""),
        "file_path": tool_info.get("file_path", ""),
        "prompt": tool_info.get("user_prompt", ""),
        "session_id": raw.get("trajectory_id", ""),
        "raw": raw,
    }


_NORMALIZERS = {
    "claude-code": _normalize_claude_code,
    "cursor": _normalize_cursor,
    "codex-cli": _normalize_codex,
    "grok-build": _normalize_grok,
    "windsurf": _normalize_windsurf,
}


def normalize_input(raw: dict, agent: str) -> dict:
    """Normalize tool-specific stdin JSON into canonical format.

    Args:
        raw: The raw JSON payload from stdin
        agent: Detected agent name (from detect_agent)

    Returns:
        Canonical dict with event, tool_name, command, file_path, prompt, session_id, raw
    """
    if not raw:
        return {
            "event": "", "tool_name": "", "command": "",
            "file_path": "", "prompt": "", "session_id": "", "raw": {},
        }

    normalizer = _NORMALIZERS.get(agent, _normalize_claude_code)
    return normalizer(raw)


# --- Output normalization ---


def normalize_output(
    event: str,
    message: str,
    blocked: bool,
    agent: str,
) -> str:
    """Convert canonical response to tool-specific JSON output.

    Args:
        event: Canonical event name
        message: Message text to inject
        blocked: Whether to block the tool call
        agent: Target agent name

    Returns:
        JSON string ready to print to stdout
    """
    if agent == "windsurf":
        result = {
            "decision": "deny" if blocked else "allow",
        }
        if blocked:
            result["reason"] = message
        else:
            result["message"] = message
        return json.dumps(result)

    # Claude Code, Cursor, Codex CLI, Grok Build all use the same output format
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": message,
        }
    })
