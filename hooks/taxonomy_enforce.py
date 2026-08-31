#!/usr/bin/env python3
"""Taxonomy enforcement hook — ensures Agent subagents use the right model tier.

PreToolUse hook for Agent tool calls. Checks that the model parameter
matches the agent_taxonomy.py rules for the task type.

Warns if:
- Agent spawned without model parameter (defaults are wasteful)
- Expensive model used for cheap tasks (file search, lint)
- Cheap model used for expensive tasks (architecture, security audit)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Optional

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
    """Check if model matches expected tier. Blocks on mismatches or missing model.

    Every Agent call MUST specify a model parameter. Tier mismatches are blocked.
    """
    # No model specified — always block
    if not model:
        tier_suggestions = {
            "cheap": "haiku",
            "mid": "sonnet",
            "expensive": "opus",
        }
        suggested = tier_suggestions.get(expected_tier, "sonnet")
        return {
            "block": True,
            "reason": f"Agent call missing model parameter. Set model=\"{suggested}\" for this task.",
        }

    model_lower = model.lower()
    actual_tier = "mid"  # default
    for model_name, tier in MODEL_TIERS.items():
        if model_name in model_lower:
            actual_tier = tier
            break

    # Expensive model on clearly cheap task = waste
    if actual_tier == "expensive" and expected_tier == "cheap":
        return {
            "block": True,
            "reason": f"Expensive model ({model}) used for a cheap task (file search/lint). Use haiku instead.",
        }

    # Cheap model on clearly expensive task = risk
    if actual_tier == "cheap" and expected_tier == "expensive":
        return {
            "block": True,
            "reason": f"Cheap model ({model}) used for deep reasoning task (architecture/security). Use opus or fable instead.",
        }

    return {"block": False}


# Keywords indicating the agent will write/change code (needs TDD)
IMPLEMENTATION_KEYWORDS = [
    "implement", "build", "create", "add", "write",
    "fix", "debug", "repair", "patch",
    "refactor", "restructure", "rewrite",
    "feature", "endpoint", "handler", "component",
]

# Keywords indicating the agent is read-only (no TDD needed)
READONLY_KEYWORDS = [
    "search", "find", "grep", "glob", "list", "count",
    "review", "audit", "check", "analyze", "evaluate", "assess",
    "read", "explore", "look", "examine",
]

TDD_INJECTION = (
    "MANDATORY: Write a FAILING test FIRST before implementing any code. "
    "Return the failing test output as proof before proceeding to implementation. "
    "Test file must be edited BEFORE source file."
)


def get_tdd_injection(description: str) -> Optional[str]:
    """Return TDD injection text if the agent prompt is implementation-like.

    Returns None for read-only tasks (search, review, etc.).
    """
    desc_lower = description.lower()

    # If it's clearly read-only, skip
    for keyword in READONLY_KEYWORDS:
        if keyword in desc_lower:
            return None

    # If it's implementation-like, inject
    for keyword in IMPLEMENTATION_KEYWORDS:
        if keyword in desc_lower:
            return TDD_INJECTION

    return None


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

    # Block on model violations
    if result.get("block"):
        output = json.dumps({
            "decision": "block",
            "reason": f"TAXONOMY BLOCK: {result['reason']}",
        })
        sys.stdout.write(output)
        sys.stdout.flush()
        return 0

    # TDD injection for implementation-like agent prompts
    tdd_text = get_tdd_injection(description)
    if tdd_text:
        output = json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": f"TDD ENFORCEMENT: {tdd_text}",
            }
        })
        sys.stdout.write(output)
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
