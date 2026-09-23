"""Auto-detect which AI coding tool is running.

Detection priority (fast to slow):
1. AGENT_TOOLKIT_TOOL env var (manual override)
2. Tool-specific env vars (CLAUDECODE, GROK_SESSION_ID, etc.)
3. Stdin JSON fields (cursor_version, trajectory_id, etc.)
4. Filesystem (~/.claude/, ~/.grok/, etc.)

Used by install.sh and session_init to load the right config format.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

SUPPORTED_AGENTS = [
    "claude-code",
    "cursor",
    "codex-cli",
    "grok-build",
    "windsurf",
]

# --- Layer 1: Env var detection ---

# (env_var_name, expected_value_or_None_for_any, agent_name)
_ENV_CHECKS = [
    ("CLAUDECODE", "1", "claude-code"),
    ("GROK_SESSION_ID", None, "grok-build"),
    ("GROK_HOOK_EVENT", None, "grok-build"),
    ("CODEX_SANDBOX", None, "codex-cli"),
    ("CODEX_THREAD_ID", None, "codex-cli"),
    ("CURSOR_CLI", None, "cursor"),
    ("CURSOR_AGENT", "1", "cursor"),
]


def detect_from_env() -> Optional[str]:
    """Check env vars for tool detection. Returns agent name or None."""
    # Manual override — highest priority
    override = os.environ.get("AGENT_TOOLKIT_TOOL", "")
    if override and override in SUPPORTED_AGENTS:
        return override

    for var_name, expected_value, agent_name in _ENV_CHECKS:
        value = os.environ.get(var_name, "")
        if expected_value is not None:
            if value == expected_value:
                return agent_name
        else:
            if value:
                return agent_name

    return None


# --- Layer 2: Stdin JSON detection ---


def detect_from_stdin(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    """Check stdin JSON payload for tool-specific fields. Returns agent name or None."""
    if not payload or not isinstance(payload, dict):
        return None

    # Cursor: has cursor_version field
    if payload.get("cursor_version"):
        return "cursor"

    # Windsurf: has trajectory_id or agent_action_name
    if payload.get("trajectory_id") or payload.get("agent_action_name"):
        return "windsurf"

    # Grok Build: uses camelCase hookEventName (not hook_event_name)
    if "hookEventName" in payload and "hook_event_name" not in payload:
        return "grok-build"

    # Codex CLI: has turn_id field
    if payload.get("turn_id"):
        return "codex-cli"

    # Claude Code: transcript_path contains .claude
    transcript = payload.get("transcript_path", "")
    if ".claude" in str(transcript):
        return "claude-code"

    # Claude Code: has hook_event_name (PascalCase, underscore-separated)
    if payload.get("hook_event_name") and payload.get("session_id"):
        return "claude-code"

    return None


# --- Layer 3: Filesystem detection ---

_FS_CHECKS = [
    (".claude", "claude-code"),
    (".grok", "grok-build"),
    (".codex", "codex-cli"),
    (".cursor", "cursor"),
    (".windsurf", "windsurf"),
    (".devin", "windsurf"),
]


def detect_from_filesystem() -> Optional[str]:
    """Check home directory for tool-specific directories. Returns agent name or None."""
    home = Path.home()
    for dirname, agent_name in _FS_CHECKS:
        if (home / dirname).is_dir():
            return agent_name
    return None


# --- Main detection ---


def detect_agent(stdin_payload: Optional[Dict[str, Any]] = None) -> str:
    """Detect which AI coding tool is running.

    Checks in order: env vars → stdin JSON → filesystem.
    Returns agent name string, or "unknown" if no match.
    """
    result = detect_from_env()
    if result:
        return result

    result = detect_from_stdin(stdin_payload)
    if result:
        return result

    result = detect_from_filesystem()
    if result:
        return result

    return "unknown"
