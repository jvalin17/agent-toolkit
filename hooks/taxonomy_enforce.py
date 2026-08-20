#!/usr/bin/env python3
"""Taxonomy enforcement hook — ensures Agent subagents use the right model tier.

PreToolUse hook for Agent tool calls. Checks that the model parameter
matches the agent_taxonomy.py rules for the task type.

Warns if:
- Agent spawned without model parameter (defaults are wasteful)
- Expensive model used for cheap tasks (file search, lint)
- Cheap model used for expensive tasks (architecture, security audit)
"""

import json
import re
import sys
from pathlib import Path

# Add roles/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "roles"))

# Task keywords → expected tier
CHEAP_KEYWORDS = [
    "file search", "search for", "find file", "grep", "glob",
    "lint", "format", "boilerplate", "scaffold",
    "list", "count", "check if",
]

EXPENSIVE_KEYWORDS = [
    "architecture", "architect", "design system",
    "security audit", "security review", "threat model",
    "complex debug", "cross-module", "multi-file debug",
    "synthesize", "merge", "evaluate", "assess",
    "migration plan", "decompose task",
]

MODEL_TIERS = {
    "haiku": "cheap",
    "sonnet": "mid",
    "opus": "expensive",
    "fable": "expensive",
}


def detect_task_tier(description: str) -> str:
    """Detect expected tier from agent description."""
    desc_lower = description.lower()

    for keyword in CHEAP_KEYWORDS:
        if keyword in desc_lower:
            return "cheap"

    for keyword in EXPENSIVE_KEYWORDS:
        if keyword in desc_lower:
            return "expensive"

    return "mid"  # default


def check_model_match(model: str, expected_tier: str) -> dict:
    """Check if model matches expected tier. Returns warning only on clear mismatches.

    Vague tasks (mid tier) are fine with any model — no warning.
    Only warn when expensive↔cheap mismatch is clear.
    """
    # Vague/mid tasks — any model is fine
    if expected_tier == "mid":
        return {"warn": False}

    # No model + clear tier → suggest, don't warn
    if not model and expected_tier in ("cheap", "expensive"):
        suggestion = "haiku" if expected_tier == "cheap" else "opus/fable"
        return {
            "warn": False,
            "suggestion": f"Consider using {suggestion} for this task.",
        }

    if not model:
        return {"warn": False}

    model_lower = model.lower()
    actual_tier = "mid"  # default
    for model_name, tier in MODEL_TIERS.items():
        if model_name in model_lower:
            actual_tier = tier
            break

    # Only warn on clear mismatches
    # Expensive model on clearly cheap task = waste
    if actual_tier == "expensive" and expected_tier == "cheap":
        return {
            "warn": True,
            "message": f"Expensive model ({model}) used for a cheap task (file search/lint). Use haiku instead.",
        }

    # Cheap model on clearly expensive task = risk
    if actual_tier == "cheap" and expected_tier == "expensive":
        return {
            "warn": True,
            "message": f"Cheap model ({model}) used for deep reasoning task (architecture/security). Use opus or fable instead.",
        }

    return {"warn": False}


def main() -> int:
    """PreToolUse hook — check Agent tool model parameter."""
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return 0

    tool_name = event.get("tool_name", "")
    if tool_name != "Agent":
        return 0

    tool_input = event.get("tool_input", {})
    description = tool_input.get("description", "") or tool_input.get("prompt", "")
    model = tool_input.get("model", "")

    expected_tier = detect_task_tier(description)
    result = check_model_match(model, expected_tier)

    if result.get("warn"):
        # Output warning as additional context — don't block, but inform
        output = json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"TAXONOMY WARNING: {result['message']}",
            }
        })
        sys.stdout.write(output)
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
