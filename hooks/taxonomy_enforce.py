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
    """Check if model matches expected tier. Returns warning if mismatch."""
    if not model:
        return {
            "warn": True,
            "message": "Agent spawned without model parameter. Set model='haiku' for cheap tasks, 'sonnet' for implementation, 'opus'/'fable' for reasoning.",
        }

    model_lower = model.lower()
    actual_tier = "mid"  # default
    for model_name, tier in MODEL_TIERS.items():
        if model_name in model_lower:
            actual_tier = tier
            break

    # Check for waste: expensive model on cheap task
    if actual_tier == "expensive" and expected_tier == "cheap":
        return {
            "warn": True,
            "message": f"Expensive model ({model}) used for a cheap task. Use haiku instead.",
        }

    # Check for risk: cheap model on expensive task
    if actual_tier == "cheap" and expected_tier == "expensive":
        return {
            "warn": True,
            "message": f"Cheap model ({model}) used for a task requiring deep reasoning. Use opus or fable instead.",
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
