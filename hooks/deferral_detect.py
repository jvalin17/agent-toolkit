#!/usr/bin/env python3
"""Anti-deferral hook — detects when the model suggests deferring work.

Fires on UserPromptSubmit. Reads the session transcript, finds the last
assistant message, and scans it for deferral patterns like "new session",
"too complex", "continue later", "running low on context".

If detected, injects a counter-message with actual session stats so the
model can't argue with fabricated context pressure.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from session_log import find_latest_session_log
from session_state import SESSION_DIR, STATE_FILENAME, HARD_THRESHOLD_BYTES

# Patterns that indicate the model is trying to defer work.
# Each pattern is designed to avoid false positives on normal usage
# of words like "session" or "context" in technical discussion.
DEFERRAL_PATTERNS = [
    re.compile(r"new\s+session", re.IGNORECASE),
    re.compile(r"fresh\s+session", re.IGNORECASE),
    re.compile(r"continue\s+(this\s+)?(later|next|tomorrow)", re.IGNORECASE),
    re.compile(r"pick\s+(this\s+)?up\s+(next|later|in\s+a)", re.IGNORECASE),
    re.compile(r"defer\s+(this|the|it)", re.IGNORECASE),
    re.compile(r"running\s+low\s+on\s+context", re.IGNORECASE),
    re.compile(r"context\s+(limit|window)\s*(is\s+)?(approach|near|running)", re.IGNORECASE),
    re.compile(r"approaching\s+(the\s+)?context\s+(limit|window)", re.IGNORECASE),
    re.compile(r"too\s+complex\s+to\s+(finish|complete|do)\s+(now|here|in\s+this)", re.IGNORECASE),
    re.compile(r"start\s+fresh", re.IGNORECASE),
    re.compile(r"wrap\s+up\s*(and|,)?\s*(start|begin|open)\s*(a\s+)?(new|fresh)", re.IGNORECASE),
]


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


def detect_deferral(text: str) -> Optional[str]:
    """Scan text for deferral patterns. Returns matched pattern or None."""
    for pattern in DEFERRAL_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None


def _get_session_stats() -> dict:
    """Read current session stats from state file."""
    state_file = Path(SESSION_DIR) / STATE_FILENAME
    try:
        if state_file.is_file():
            data = json.loads(state_file.read_text())
            return {
                "exchanges": data.get("exchanges", 0),
                "bytes": data.get("cumulative_output_bytes", 0),
                "bytes_limit": HARD_THRESHOLD_BYTES,
            }
    except (json.JSONDecodeError, OSError):
        pass
    return {"exchanges": 0, "bytes": 0, "bytes_limit": HARD_THRESHOLD_BYTES}


def run_deferral_check(stdin_input: str) -> Tuple[int, str]:
    """Main entry point. Returns (exit_code, hook_output)."""
    try:
        hook_input = json.loads(stdin_input)
    except (json.JSONDecodeError, TypeError):
        return 0, ""

    log_path = find_latest_session_log()
    if not log_path:
        return 0, ""

    last_text = extract_last_assistant_text(log_path)
    if not last_text:
        return 0, ""

    matched = detect_deferral(last_text)
    if not matched:
        return 0, ""

    stats = _get_session_stats()
    pct_used = (stats["bytes"] / stats["bytes_limit"] * 100) if stats["bytes_limit"] else 0

    counter = (
        f"DEFERRAL DETECTED: The previous response suggested deferring work. "
        f"Session stats: {stats['exchanges']} exchanges, "
        f"{stats['bytes']:,}/{stats['bytes_limit']:,} bytes ({pct_used:.0f}% used). "
        f"Do NOT suggest new sessions, deferring, or stopping unless the session monitor "
        f"has issued a HARD STOP. Continue working on the task."
    )

    output = json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": counter,
        }
    })
    return 0, output


def main() -> int:
    stdin_input = sys.stdin.read()
    exit_code, output = run_deferral_check(stdin_input)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
