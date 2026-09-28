#!/usr/bin/env python3
"""Canary context-loss detection hook.

Fires on UserPromptSubmit. Reads the last assistant message from the
session log and checks whether it starts with the configured canary word.

If the canary is missing, injects a suggestion that context may be
degrading and a new session might help. This is hook-verified — the
agent cannot fake compliance.

Configuration: set "canary": "YourWord" in gates.json.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_hook import get_config_value, load_gate_config
from session_log import find_latest_session_log


def extract_last_assistant_text(log_path: Path) -> str:
    """Read the JSONL log and return the text of the last assistant message."""
    if not log_path or not log_path.is_file():
        return ""

    last_text = ""
    try:
        for line in log_path.read_text(errors="ignore").split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if entry.get("type") != "assistant":
                    continue
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, str):
                    last_text = content
                elif isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                    if parts:
                        last_text = " ".join(parts)
            except (json.JSONDecodeError, TypeError, KeyError):
                continue
    except OSError:
        return ""

    return last_text


def check_canary_in_text(text: str, canary: str) -> Optional[str]:
    """Check if canary word appears at the start of the text.

    Returns None if canary is present (or feature is off).
    Returns a warning string if canary is missing.
    """
    if not canary:
        return None
    if not text:
        return None

    # Check if text starts with canary (case-insensitive, allowing punctuation after)
    pattern = re.compile(
        r"^\s*" + re.escape(canary) + r"\b",
        re.IGNORECASE,
    )
    if pattern.search(text):
        return None

    return (
        f"CANARY MISSING: Expected \"{canary}\" at the start of the response. "
        f"This may indicate context degradation. "
        f"Consider starting a new session if responses feel off."
    )


def run_canary_check(stdin_input: str) -> Tuple[int, str]:
    """Main entry point. Returns (exit_code, hook_output)."""
    try:
        json.loads(stdin_input)
    except (json.JSONDecodeError, TypeError):
        return 0, ""

    config = load_gate_config(Path.cwd())
    canary = get_config_value(config, "canary", "Hey")
    if not canary:
        return 0, ""

    log_path = find_latest_session_log()
    if not log_path:
        return 0, ""

    last_text = extract_last_assistant_text(log_path)
    if not last_text:
        return 0, ""

    warning = check_canary_in_text(last_text, canary)
    if not warning:
        return 0, ""

    output = json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": warning,
        }
    })
    return 0, output


def main() -> int:
    stdin_input = sys.stdin.read()
    exit_code, output = run_canary_check(stdin_input)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
