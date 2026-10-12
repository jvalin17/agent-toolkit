#!/usr/bin/env python3
"""Multi-tool config generator — generate hook configs for all supported AI coding tools.

Reads the toolkit's hook definitions and generates equivalent configs for:
- Claude Code (settings.json)
- Cursor (.cursor/hooks.json)
- Codex CLI (.codex/config.toml)
- Grok Build (.grok/hooks.json)
- Windsurf (hooks.json)

Usage:
    python3 scripts/config_generator.py [--tool TOOL] [--output DIR]

Without --tool, generates all configs. Without --output, prints to stdout.
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

SUPPORTED_TOOLS = ["claude-code", "cursor", "codex-cli", "grok-build", "windsurf"]

# Hooks that are Claude Code-specific and have no equivalent elsewhere
CLAUDE_ONLY_HOOKS = {"check_doc_write.sh", "check-doc-commit.sh", "check-doc-write.sh"}


@dataclass
class ToolkitHook:
    """A single hook definition from the toolkit."""
    event: str          # PreToolUse, PostToolUse, UserPromptSubmit, etc.
    matcher: str        # Tool name filter (e.g., "Bash", "Edit|Write", "")
    command: str        # Command to run
    timeout: int = 5    # Timeout in seconds
    status_message: str = ""  # Optional status message


# --- Collect hooks from toolkit ---


def collect_toolkit_hooks(toolkit_path: Path) -> List[ToolkitHook]:
    """Scan the toolkit's hook scripts and build the canonical hook list.

    This is the source of truth — all tool-specific generators read from this.
    """
    hooks_dir = toolkit_path / "hooks"
    tp = str(toolkit_path)

    hooks = [
        # --- PreToolUse ---
        ToolkitHook("PreToolUse", "Agent",
                     f"python3 {tp}/hooks/taxonomy_enforce.py", 5),
        ToolkitHook("PreToolUse", "Bash",
                     f"python3 {tp}/hooks/gate_hook.py", 5,
                     "Checking quality gates..."),
        ToolkitHook("PreToolUse", "Bash|Write|Edit|Skill|mcp__agent-toolkit__stamp_skill",
                     f"python3 {tp}/hooks/session_monitor.py", 5,
                     "Session monitor..."),
        ToolkitHook("PreToolUse", "Edit|Write",
                     f"python3 {tp}/hooks/skill_enforce.py", 5,
                     "Checking skill workflow..."),
        ToolkitHook("PreToolUse", "Edit|Write",
                     f"python3 {tp}/hooks/tdd_enforce.py", 5),
        ToolkitHook("PreToolUse", "Skill",
                     f"bash {tp}/update.sh || true", 10,
                     "Checking for toolkit updates..."),

        # --- PostToolUse ---
        ToolkitHook("PostToolUse", "",
                     f"python3 {tp}/hooks/session_monitor.py", 5,
                     "Session monitor (post-tool)..."),
        ToolkitHook("PostToolUse", "Bash",
                     f"python3 {tp}/hooks/gate_cleanup.py", 5),
        ToolkitHook("PostToolUse", "Skill",
                     f"python3 {tp}/hooks/skill_passed.py", 5),

        # --- UserPromptSubmit ---
        ToolkitHook("UserPromptSubmit", "",
                     f"python3 {tp}/hooks/route_to_skill.py", 5),
        ToolkitHook("UserPromptSubmit", "",
                     f"python3 {tp}/hooks/session_monitor.py", 5),
        ToolkitHook("UserPromptSubmit", "",
                     f"python3 {tp}/hooks/deferral_detect.py", 5),

        # --- SessionStart ---
        ToolkitHook("SessionStart", "startup",
                     f"python3 {tp}/hooks/session_init.py", 5),
        ToolkitHook("SessionStart", "compact",
                     f"python3 {tp}/hooks/session_init.py", 5),
        # Compaction detection — canonical event, mapped per host by
        # NATIVE_COMPACTION (Claude Code: SessionStart/compact, Cursor: preCompact, ...).
        ToolkitHook(COMPACTION_EVENT, "",
                     f"python3 {tp}/hooks/session_monitor.py", 5,
                     "Session monitor (compact)..."),
    ]

    return hooks


# --- Compaction (canonical event, per-host native name) ---

# "PostCompact" is not a hook event on any supported host. Each host delivers
# compaction differently; session_monitor.COMPACTION_EVENTS accepts all of these.
COMPACTION_EVENT = "Compaction"
NATIVE_COMPACTION: Dict[str, tuple] = {
    "claude-code": ("SessionStart", "compact"),
    "grok-build": ("SessionStart", "compact"),
    "codex-cli": ("SessionStart", "compact"),
    "cursor": ("preCompact", ""),
    "windsurf": ("post-compact", ""),
}


def _native_event(h: ToolkitHook, tool: str) -> tuple:
    """(event, matcher) as the host names them; non-compaction hooks pass through."""
    if h.event == COMPACTION_EVENT:
        return NATIVE_COMPACTION[tool]
    return h.event, h.matcher


# --- Claude Code ---


def generate_claude_code(hooks: List[ToolkitHook], toolkit_path: Path) -> str:
    """Generate Claude Code settings.json hooks section."""
    config: Dict[str, list] = {}

    for h in hooks:
        event, matcher = _native_event(h, "claude-code")
        if event not in config:
            config[event] = []

        hook_entry = {"type": "command", "command": h.command, "timeout": h.timeout}
        if h.status_message:
            hook_entry["statusMessage"] = h.status_message

        # Group by matcher
        existing = None
        for group in config[event]:
            if group["matcher"] == matcher:
                existing = group
                break

        if existing:
            existing["hooks"].append(hook_entry)
        else:
            config[event].append({"matcher": matcher, "hooks": [hook_entry]})

    return json.dumps({"hooks": config}, indent=2)


# --- Cursor ---

# Cursor event name mapping (PascalCase, same as Claude Code since v1.7)
CURSOR_EVENT_MAP = {
    "PreToolUse": "preToolUse",
    "PostToolUse": "postToolUse",
    "UserPromptSubmit": "beforeSubmitPrompt",
    "SessionStart": "sessionStart",
}

# Cursor matcher mapping
CURSOR_MATCHER_MAP = {
    "Bash": "Shell",
    "Edit": "Write",  # Cursor uses Write for all edits
}


def _cursor_matcher(matcher: str) -> str:
    """Convert Claude Code matcher to Cursor equivalent."""
    if not matcher:
        return ""
    parts = matcher.split("|")
    converted = []
    for p in parts:
        converted.append(CURSOR_MATCHER_MAP.get(p, p))
    return "|".join(sorted(set(converted)))


def generate_cursor(hooks: List[ToolkitHook], toolkit_path: Path) -> str:
    """Generate Cursor .cursor/hooks.json config."""
    config: Dict[str, list] = {}

    for h in hooks:
        native_event, native_matcher = _native_event(h, "cursor")
        event = CURSOR_EVENT_MAP.get(native_event, native_event)
        if event not in config:
            config[event] = []

        hook_entry = {
            "type": "command",
            "command": h.command,
            "timeout": h.timeout,
        }
        if h.status_message:
            hook_entry["statusMessage"] = h.status_message

        matcher = _cursor_matcher(native_matcher)
        existing = None
        for group in config[event]:
            if group.get("matcher", "") == matcher:
                existing = group
                break

        if existing:
            existing["hooks"].append(hook_entry)
        else:
            entry = {"hooks": [hook_entry]}
            if matcher:
                entry["matcher"] = matcher
            config[event].append(entry)

    return json.dumps({"hooks": config}, indent=2)


# --- Codex CLI ---


def generate_codex_cli(hooks: List[ToolkitHook], toolkit_path: Path) -> str:
    """Generate Codex CLI .codex/config.toml hooks section."""
    lines = ["# Agent Toolkit hooks for Codex CLI", "# Place in .codex/config.toml", ""]

    # Group hooks by native event
    by_event: Dict[str, List[tuple]] = {}
    for h in hooks:
        event, matcher = _native_event(h, "codex-cli")
        by_event.setdefault(event, []).append((h, matcher))

    lines.append("[hooks]")
    lines.append("")

    for event, event_hooks in by_event.items():
        for h, matcher in event_hooks:
            lines.append(f"[[hooks.{event}]]")
            lines.append(f'command = "{h.command}"')
            lines.append(f"timeout = {h.timeout}")
            if matcher:
                lines.append(f'matcher = "{matcher}"')
            if h.status_message:
                lines.append(f'status_message = "{h.status_message}"')
            lines.append("")

    return "\n".join(lines)


# --- Grok Build ---


def generate_grok_build(hooks: List[ToolkitHook], toolkit_path: Path) -> str:
    """Generate Grok Build .grok/hooks.json config.

    Grok Build uses the same hook format as Claude Code — it reads CLAUDE.md
    and has compatible PreToolUse/PostToolUse events.
    """
    config: Dict[str, list] = {}

    for h in hooks:
        event, matcher = _native_event(h, "grok-build")
        if event not in config:
            config[event] = []

        hook_entry = {"type": "command", "command": h.command, "timeout": h.timeout}
        if h.status_message:
            hook_entry["statusMessage"] = h.status_message

        existing = None
        for group in config[event]:
            if group.get("matcher", "") == matcher:
                existing = group
                break

        if existing:
            existing["hooks"].append(hook_entry)
        else:
            entry = {"matcher": matcher, "hooks": [hook_entry]}
            config[event].append(entry)

    return json.dumps({"hooks": config}, indent=2)


# --- Windsurf ---

WINDSURF_EVENT_MAP = {
    "PreToolUse": "pre-edit",
    "PostToolUse": "post-edit",
    "UserPromptSubmit": "pre-prompt",
    "SessionStart": "session-start",
}


def generate_windsurf(hooks: List[ToolkitHook], toolkit_path: Path) -> str:
    """Generate Windsurf hooks.json config."""
    config: Dict[str, list] = {}

    for h in hooks:
        native_event, native_matcher = _native_event(h, "windsurf")
        event = WINDSURF_EVENT_MAP.get(native_event, native_event)
        if event not in config:
            config[event] = []

        hook_entry = {
            "type": "command",
            "command": h.command,
            "timeout": h.timeout,
        }
        if native_matcher:
            hook_entry["matcher"] = native_matcher
        if h.status_message:
            hook_entry["statusMessage"] = h.status_message

        config[event].append(hook_entry)

    return json.dumps({"hooks": config}, indent=2)


# --- Dispatch ---

GENERATORS = {
    "claude-code": generate_claude_code,
    "cursor": generate_cursor,
    "codex-cli": generate_codex_cli,
    "grok-build": generate_grok_build,
    "windsurf": generate_windsurf,
}


def generate_all(hooks: List[ToolkitHook], toolkit_path: Path) -> Dict[str, str]:
    """Generate configs for all supported tools."""
    return {tool: gen(hooks, toolkit_path) for tool, gen in GENERATORS.items()}


# --- CLI ---

TOOL_FILENAMES = {
    "claude-code": "settings.json",
    "cursor": "hooks.json",
    "codex-cli": "config.toml",
    "grok-build": "hooks.json",
    "windsurf": "hooks.json",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate hook configs for AI coding tools"
    )
    parser.add_argument(
        "--tool", choices=SUPPORTED_TOOLS,
        help="Generate for a specific tool (default: all)",
    )
    parser.add_argument(
        "--output", type=Path,
        help="Output directory (default: print to stdout)",
    )
    parser.add_argument(
        "--toolkit-path", type=Path, default=Path(__file__).resolve().parent.parent,
        help="Path to the toolkit root",
    )
    args = parser.parse_args()

    hooks = collect_toolkit_hooks(args.toolkit_path)

    if args.tool:
        result = GENERATORS[args.tool](hooks, args.toolkit_path)
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            out = args.output / TOOL_FILENAMES[args.tool]
            out.write_text(result)
            print(f"Written: {out}")
        else:
            print(result)
    else:
        results = generate_all(hooks, args.toolkit_path)
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            for tool, content in results.items():
                out = args.output / TOOL_FILENAMES[tool]
                out.write_text(content)
                print(f"Written: {out}")
        else:
            for tool, content in results.items():
                print(f"\n{'='*60}")
                print(f"  {tool} ({TOOL_FILENAMES[tool]})")
                print(f"{'='*60}\n")
                print(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
