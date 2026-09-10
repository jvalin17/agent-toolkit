#!/usr/bin/env python3
"""MCP server for agent-toolkit — exposes role/orchestration tools.

Wraps existing Python modules (agent_taxonomy, orchestrator, context)
as MCP tools callable by any AI tool via the Model Context Protocol.

All tools are read-only lookups. No state mutation, no auth needed.
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Add roles/ to Python path (same pattern as all existing tests and hooks)
TOOLKIT_ROOT = Path(__file__).resolve().parent.parent
ROLES_DIR = TOOLKIT_ROOT / "roles"
SKILLS_DIR = TOOLKIT_ROOT / "skills"
AGENTS_DIR = TOOLKIT_ROOT / "agents"
sys.path.insert(0, str(ROLES_DIR))

from fastmcp import FastMCP

mcp = FastMCP(
    "agent-toolkit",
    instructions=(
        "Agent Toolkit provides 19 specialized roles, 13 skills, and 9 agents "
        "for software engineering. Use select_agent to pick the right model for "
        "a task. Use build_plan to get a deterministic orchestration plan. "
        "Use list_roles/list_skills/list_agents for discovery."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1: select_agent — pick the best model for a task type
# ---------------------------------------------------------------------------
@mcp.tool(annotations={"readOnlyHint": True})
def select_agent(
    task_type: str,
    available: Optional[list[str]] = None,
) -> dict:
    """Select the best model/agent for a task type.

    Returns the cheapest capable model. Task types include:
    fetch, file_search, lint_check, boilerplate (cheap/haiku),
    code_review, code_generation, bug_fix, test_writing (mid/sonnet),
    architecture_decision, security_audit, synthesize, quality_review (expensive/opus).

    Args:
        task_type: Key from the task taxonomy (e.g., "fetch", "architecture_decision")
        available: Optional list of available model names. Defaults to all.
    """
    try:
        from agent_taxonomy import select_agent as _select_agent
        return _select_agent(task_type, available=available)
    except Exception as e:
        return {"error": str(e), "hint": "Check task_type is valid. Use list_task_types for options."}


# ---------------------------------------------------------------------------
# Tool 2: build_plan — deterministic orchestration plan
# ---------------------------------------------------------------------------
@mcp.tool(annotations={"readOnlyHint": True})
def build_plan(
    primary_role: str,
    task_type: str,
    active_roles: list[str],
) -> dict:
    """Build a deterministic orchestration plan for a task.

    The plan defines what happens in what order — skills to run, roles to invoke,
    model tiers for each step. The LLM follows the plan, it doesn't invent it.

    Args:
        primary_role: Role doing the main work (e.g., "backend", "frontend")
        task_type: One of "new_feature", "bug_fix", "refactor", "migration"
        active_roles: All currently active roles (e.g., ["backend", "dba", "security"])
    """
    try:
        from orchestrator import build_orchestration_plan
        return build_orchestration_plan(
            primary_role=primary_role,
            task_type=task_type,
            active_roles=active_roles,
            roles_dir=ROLES_DIR,
        )
    except Exception as e:
        return {"error": str(e), "hint": "Check role names with list_roles."}


# ---------------------------------------------------------------------------
# Tool 3: plan_to_text — render plan as injectable context
# ---------------------------------------------------------------------------
@mcp.tool(annotations={"readOnlyHint": True})
def plan_to_text(plan: dict) -> str:
    """Convert an orchestration plan to injectable text.

    Takes the output of build_plan and renders it as plain text that can be
    injected into any LLM's context. Includes step sequence, model assignments,
    role checklists, and anti-patterns.

    Args:
        plan: The plan dict returned by build_plan
    """
    try:
        from orchestrator import plan_to_context
        return plan_to_context(plan, roles_dir=ROLES_DIR)
    except Exception as e:
        return f"Error: {e}. Ensure plan is a valid dict from build_plan."


# ---------------------------------------------------------------------------
# Tool 4: get_role_context — detect roles and generate context for any AI tool
# ---------------------------------------------------------------------------
@mcp.tool(annotations={"readOnlyHint": True})
def get_role_context(
    project_dir: str,
    roles: Optional[list[str]] = None,
    max_roles: int = 4,
) -> dict:
    """Detect which roles apply to a project and generate context text.

    Scans the project for signals (package.json, requirements.txt, Dockerfile, etc.)
    and selects up to max_roles matching roles. Returns structured context that can
    be injected into any AI tool's system prompt.

    Args:
        project_dir: Path to the project to analyze
        roles: Optional override — specific role names instead of auto-detection
        max_roles: Maximum number of roles to include (default 4)
    """
    try:
        from context import get_context_json
        project_path = Path(project_dir)
        if not project_path.is_dir():
            return {"error": f"Directory not found: {project_dir}", "hint": "Provide a valid project directory path."}
        result = get_context_json(
            project_dir=project_path,
            roles_dir=ROLES_DIR,
            config_roles=roles,
            max_roles=max_roles,
        )
        return json.loads(result) if isinstance(result, str) else result
    except Exception as e:
        return {"error": str(e), "hint": "Check project_dir exists and is accessible."}


# ---------------------------------------------------------------------------
# Tool 5: list_roles — discover available roles
# ---------------------------------------------------------------------------
@mcp.tool(annotations={"readOnlyHint": True})
def list_roles() -> list[dict]:
    """List all available roles with their metadata.

    Returns role names and descriptions from roles/*/role.md frontmatter.
    """
    roles = []
    try:
        for role_dir in sorted(ROLES_DIR.iterdir()):
            role_md = role_dir / "role.md"
            if role_md.is_file():
                content = role_md.read_text()
                name = role_dir.name
                description = ""
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        for line in parts[1].split("\n"):
                            if line.strip().startswith("description:"):
                                description = line.split(":", 1)[1].strip().strip('"')
                                break
                roles.append({"name": name, "description": description})
    except Exception as e:
        return [{"error": str(e)}]
    return roles


# ---------------------------------------------------------------------------
# Tool 6: list_skills — discover available skills
# ---------------------------------------------------------------------------
@mcp.tool(annotations={"readOnlyHint": True})
def list_skills() -> list[dict]:
    """List all available skills with their metadata.

    Returns skill names and descriptions from skills/*/SKILL.md frontmatter.
    """
    skills = []
    try:
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.is_file():
                content = skill_md.read_text()
                name = skill_dir.name
                description = ""
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        for line in parts[1].split("\n"):
                            if line.strip().startswith("description:"):
                                description = line.split(":", 1)[1].strip().strip('"')
                                break
                skills.append({"name": name, "description": description})
    except Exception as e:
        return [{"error": str(e)}]
    return skills


# ---------------------------------------------------------------------------
# Tool 7: list_agents — discover available sub-agents
# ---------------------------------------------------------------------------
@mcp.tool(annotations={"readOnlyHint": True})
def list_agents() -> list[dict]:
    """List all available sub-agents with their metadata.

    Returns agent names and descriptions from agents/*.md frontmatter.
    """
    agents = []
    try:
        for agent_file in sorted(AGENTS_DIR.glob("*.md")):
            content = agent_file.read_text()
            name = agent_file.stem
            description = ""
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    for line in parts[1].split("\n"):
                        stripped = line.strip()
                        if stripped.startswith("description:"):
                            desc_val = stripped.split(":", 1)[1].strip().strip('"')
                            if desc_val:
                                description = desc_val
                            break
            agents.append({"name": name, "description": description})
    except Exception as e:
        return [{"error": str(e)}]
    return agents


# ---------------------------------------------------------------------------
# Tool 8: build_research_plan — fan-out research plan
# ---------------------------------------------------------------------------
@mcp.tool(annotations={"readOnlyHint": True})
def build_research_plan(
    query: str,
    search_count: int = 5,
) -> dict:
    """Build a parallel research plan: fan-out fetchers + synthesizer.

    Returns a structured plan with N parallel cheap search agents and
    1 expensive synthesizer. The caller executes the plan.

    Args:
        query: What to research
        search_count: How many parallel searches to run (default 5)
    """
    try:
        from agent_taxonomy import build_research_plan as _build_research_plan
        return _build_research_plan(query=query, search_count=search_count)
    except Exception as e:
        return {"error": str(e), "hint": "Check query is a non-empty string."}
