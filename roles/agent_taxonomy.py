#!/usr/bin/env python3
"""Agent taxonomy — which model/agent is best for which task.

Defines a capability matrix: task type → preferred model tier → fallback.
Used by orchestrator, research, and any code that spawns subagents.

No LLM needed. Pure lookup table + selection logic.

Usage:
  from agent_taxonomy import select_agent, TASK_TAXONOMY

  # Get best agent for a task
  agent = select_agent("fetch", available=["haiku", "sonnet", "opus"])
  # → {"model": "haiku", "reason": "mechanical fetch — cheapest capable"}

  # Get best agent when preferred isn't available
  agent = select_agent("synthesize", available=["sonnet"])
  # → {"model": "sonnet", "reason": "fallback — opus/fable unavailable"}
"""

from typing import Any, Dict, List, Optional


# Task taxonomy: what each task needs and which models handle it
# Priority order: first available model in the list is selected
TASK_TAXONOMY = {
    # --- FETCH tasks (mechanical, read-only, bounded) ---
    "fetch": {
        "description": "Clone repo, HTTP GET, download file",
        "needs": "network I/O only, no reasoning",
        "preferred": ["haiku"],
        "fallback": ["sonnet"],
        "max_tokens": 1000,
    },
    "file_search": {
        "description": "Glob, grep, find files by pattern",
        "needs": "pattern matching, no reasoning",
        "preferred": ["haiku"],
        "fallback": ["sonnet"],
        "max_tokens": 500,
    },
    "lint_check": {
        "description": "Run linter, format checker",
        "needs": "execute command, read output",
        "preferred": ["haiku"],
        "fallback": ["sonnet"],
        "max_tokens": 1000,
    },
    "boilerplate": {
        "description": "Generate scaffolding, config files",
        "needs": "template filling, minimal reasoning",
        "preferred": ["haiku", "sonnet"],
        "fallback": ["sonnet"],
        "max_tokens": 2000,
    },

    # --- UNDERSTAND tasks (analysis, extraction, moderate reasoning) ---
    "study_repo": {
        "description": "Analyze codebase patterns, extract conventions",
        "needs": "read code + identify patterns",
        "preferred": ["sonnet"],
        "fallback": ["opus", "haiku"],
        "max_tokens": 4000,
    },
    "code_review": {
        "description": "Review code for quality, bugs, anti-patterns",
        "needs": "understand code + apply rules",
        "preferred": ["sonnet"],
        "fallback": ["opus"],
        "max_tokens": 4000,
    },
    "code_generation": {
        "description": "Write new code, implement features",
        "needs": "understand spec + write correct code",
        "preferred": ["sonnet"],
        "fallback": ["opus"],
        "max_tokens": 4000,
    },
    "bug_fix": {
        "description": "Diagnose and fix bugs",
        "needs": "understand code + reason about cause",
        "preferred": ["sonnet"],
        "fallback": ["opus"],
        "max_tokens": 4000,
    },
    "test_writing": {
        "description": "Write unit/integration/E2E tests",
        "needs": "understand behavior + write assertions",
        "preferred": ["sonnet"],
        "fallback": ["opus", "haiku"],
        "max_tokens": 4000,
    },
    "research_web": {
        "description": "Search web, read articles, extract info",
        "needs": "search + read + summarize",
        "preferred": ["sonnet"],
        "fallback": ["haiku"],
        "max_tokens": 4000,
    },

    # --- REASON tasks (deep thinking, judgment, architecture) ---
    "architecture_decision": {
        "description": "Design system, choose patterns, evaluate tradeoffs",
        "needs": "deep reasoning, multi-factor analysis",
        "preferred": ["fable", "opus"],
        "fallback": ["sonnet"],
        "max_tokens": 4000,
    },
    "synthesize": {
        "description": "Merge multiple sources, resolve conflicts, rank",
        "needs": "judgment, deduplication, prioritization",
        "preferred": ["fable", "opus"],
        "fallback": ["sonnet"],
        "max_tokens": 4000,
    },
    "security_audit": {
        "description": "Review for vulnerabilities, threat modeling",
        "needs": "deep security knowledge + reasoning",
        "preferred": ["fable", "opus"],
        "fallback": ["sonnet"],
        "max_tokens": 4000,
    },
    "complex_debug": {
        "description": "Multi-file, cross-module debugging",
        "needs": "trace execution across boundaries",
        "preferred": ["fable", "opus"],
        "fallback": ["sonnet"],
        "max_tokens": 4000,
    },
    "migration_planning": {
        "description": "Plan system migration, evaluate approaches",
        "needs": "deep reasoning about tradeoffs and risks",
        "preferred": ["fable", "opus"],
        "fallback": ["sonnet"],
        "max_tokens": 4000,
    },
    "cross_role_evaluation": {
        "description": "Review output from multiple roles, resolve conflicts",
        "needs": "multi-perspective judgment",
        "preferred": ["fable", "opus"],
        "fallback": ["sonnet"],
        "max_tokens": 4000,
    },
    "task_decomposition": {
        "description": "Break complex task into subtasks, identify dependencies",
        "needs": "planning, dependency analysis",
        "preferred": ["fable", "opus"],
        "fallback": ["sonnet"],
        "max_tokens": 4000,
    },
}

# Model capabilities (for documentation and selection logic)
MODEL_CAPABILITIES = {
    "haiku": {
        "tier": "cheap",
        "good_at": ["fetching", "file search", "linting", "formatting", "boilerplate", "simple extraction"],
        "bad_at": ["architecture", "complex debugging", "security audit", "synthesis"],
        "cost_per_mtok_in": 0.25,
        "cost_per_mtok_out": 1.25,
        "speed": "fastest",
    },
    "sonnet": {
        "tier": "mid",
        "good_at": ["code generation", "bug fixes", "code review", "test writing", "research", "studying repos"],
        "bad_at": ["nothing critical — solid all-rounder"],
        "cost_per_mtok_in": 3,
        "cost_per_mtok_out": 15,
        "speed": "fast",
    },
    "opus": {
        "tier": "expensive",
        "good_at": ["architecture", "security audit", "complex debugging", "synthesis", "judgment"],
        "bad_at": ["nothing — but expensive for simple tasks"],
        "cost_per_mtok_in": 15,
        "cost_per_mtok_out": 75,
        "speed": "moderate",
    },
    "fable": {
        "tier": "flagship",
        "good_at": ["hardest problems", "architecture", "synthesis", "multi-step reasoning", "cross-role evaluation"],
        "bad_at": ["nothing — but most expensive"],
        "cost_per_mtok_in": 10,
        "cost_per_mtok_out": 50,
        "speed": "fast",
    },
}

# Model ID mapping
MODEL_IDS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-6",
    "fable": "claude-fable-5",
}


def select_agent(
    task_type: str,
    available: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Select the best agent/model for a task type.

    Args:
        task_type: Key from TASK_TAXONOMY (e.g., "fetch", "synthesize")
        available: List of available model names. Defaults to all.

    Returns:
        {"model": "haiku", "model_id": "claude-haiku-...", "reason": "...", "max_tokens": N}
    """
    if available is None:
        available = list(MODEL_IDS.keys())

    available_set = set(available)

    task = TASK_TAXONOMY.get(task_type)
    if not task:
        # Unknown task — default to sonnet
        model = "sonnet" if "sonnet" in available_set else available[0]
        return {
            "model": model,
            "model_id": MODEL_IDS.get(model, model),
            "reason": f"unknown task type '{task_type}' — defaulting to {model}",
            "max_tokens": 4000,
        }

    # Try preferred models first
    for model in task["preferred"]:
        if model in available_set:
            return {
                "model": model,
                "model_id": MODEL_IDS.get(model, model),
                "reason": f"{task['description']} — {model} is preferred",
                "max_tokens": task.get("max_tokens", 4000),
            }

    # Try fallbacks
    for model in task.get("fallback", []):
        if model in available_set:
            return {
                "model": model,
                "model_id": MODEL_IDS.get(model, model),
                "reason": f"fallback — preferred models unavailable, using {model}",
                "max_tokens": task.get("max_tokens", 4000),
            }

    # Last resort — use whatever is available
    model = available[0] if available else "sonnet"
    return {
        "model": model,
        "model_id": MODEL_IDS.get(model, model),
        "reason": f"last resort — only {model} available",
        "max_tokens": task.get("max_tokens", 4000),
    }


def build_research_plan(
    query: str,
    search_count: int = 5,
    available: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a parallel research plan: fan-out fetchers + synthesizer.

    Args:
        query: What to research
        search_count: How many parallel searches to run
        available: Available models

    Returns:
        Plan dict with fetch steps (parallel, cheap) + synthesize step (expensive)
    """
    fetcher = select_agent("research_web", available)
    synthesizer = select_agent("synthesize", available)

    return {
        "type": "parallel_research",
        "query": query,
        "steps": [
            {
                "phase": "fetch",
                "description": f"Spawn {search_count} parallel search agents",
                "agent_count": search_count,
                "model": fetcher["model"],
                "model_id": fetcher["model_id"],
                "parallel": True,
                "max_tokens": fetcher["max_tokens"],
            },
            {
                "phase": "synthesize",
                "description": "Merge all search results into structured findings",
                "agent_count": 1,
                "model": synthesizer["model"],
                "model_id": synthesizer["model_id"],
                "parallel": False,
                "max_tokens": synthesizer["max_tokens"],
            },
        ],
    }
