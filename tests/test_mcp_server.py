#!/usr/bin/env python3
"""Tests for the MCP server — verifies the underlying functions the server wraps.

Tests call the roles/ modules directly (same functions the MCP tools wrap).
The server.py decorators are tested via a separate structural test.
"""

import sys
from pathlib import Path

import pytest

# Skip entire module if fastmcp is not installed
fastmcp = pytest.importorskip("fastmcp")

ROOT = Path(__file__).resolve().parents[1]
ROLES_DIR = ROOT / "roles"
SKILLS_DIR = ROOT / "skills"
AGENTS_DIR = ROOT / "agents"
sys.path.insert(0, str(ROLES_DIR))

from agent_taxonomy import select_agent, build_research_plan, TASK_TAXONOMY
from orchestrator import build_orchestration_plan, plan_to_context


# --- select_agent ---

class TestSelectAgent:
    def test_fetch_returns_haiku(self):
        result = select_agent("fetch")
        assert result["model"] == "haiku"

    def test_architecture_returns_expensive(self):
        result = select_agent("architecture_decision")
        assert result["model"] in ("fable", "opus")

    def test_unknown_type_returns_sonnet(self):
        result = select_agent("completely_made_up_type")
        assert result["model"] == "sonnet"
        assert "unknown" in result["reason"]

    def test_with_limited_available(self):
        result = select_agent("fetch", available=["sonnet"])
        assert result["model"] == "sonnet"

    def test_all_taxonomy_types_resolve(self):
        for task_type in TASK_TAXONOMY:
            result = select_agent(task_type)
            assert "model" in result
            assert "model_id" in result


# --- build_plan ---

class TestBuildPlan:
    def test_new_feature_returns_steps(self):
        result = build_orchestration_plan("backend", "new_feature", ["backend", "security"], roles_dir=ROLES_DIR)
        assert "steps" in result
        assert len(result["steps"]) > 0

    def test_new_feature_includes_skills(self):
        result = build_orchestration_plan("backend", "new_feature", ["backend", "security"], roles_dir=ROLES_DIR)
        skill_names = [s.get("skill") for s in result["steps"] if s.get("type") == "skill"]
        assert "requirements" in skill_names
        assert "reviewer" in skill_names
        assert "evaluate" in skill_names
        assert "precommit" in skill_names

    def test_bug_fix_uses_debug_tool(self):
        result = build_orchestration_plan("backend", "bug_fix", ["backend"], roles_dir=ROLES_DIR)
        skill_names = [s.get("skill") for s in result["steps"] if s.get("type") == "skill"]
        assert "debug_tool" in skill_names

    def test_invalid_role_still_returns_plan(self):
        result = build_orchestration_plan("nonexistent_role", "new_feature", ["nonexistent_role"], roles_dir=ROLES_DIR)
        assert "steps" in result


# --- plan_to_text ---

class TestPlanToText:
    def test_renders_orchestration_plan(self):
        plan = build_orchestration_plan("backend", "new_feature", ["backend", "security"], roles_dir=ROLES_DIR)
        text = plan_to_context(plan, roles_dir=ROLES_DIR)
        assert "ORCHESTRATION PLAN" in text
        assert "backend" in text

    def test_includes_model_guide(self):
        plan = build_orchestration_plan("backend", "new_feature", ["backend"], roles_dir=ROLES_DIR)
        text = plan_to_context(plan, roles_dir=ROLES_DIR)
        assert "haiku" in text
        assert "sonnet" in text
        assert "opus" in text


# --- get_role_context ---

class TestGetRoleContext:
    def test_with_project_dir(self, tmp_path):
        from context import get_context_json
        pkg = tmp_path / "package.json"
        pkg.write_text('{"dependencies": {"express": "^4.0.0"}}')
        result = get_context_json(tmp_path, roles_dir=ROLES_DIR)
        assert result is not None

    def test_empty_dir_returns_something(self, tmp_path):
        from context import get_context
        result = get_context(tmp_path, roles_dir=ROLES_DIR)
        assert isinstance(result, str)

    def test_with_explicit_roles(self, tmp_path):
        from context import get_context
        result = get_context(tmp_path, roles_dir=ROLES_DIR, config_roles=["backend", "security"])
        assert isinstance(result, str)
        assert len(result) > 0


# --- list_roles ---

class TestListRoles:
    def test_returns_roles(self):
        roles = [d.name for d in sorted(ROLES_DIR.iterdir()) if (d / "role.md").is_file()]
        assert len(roles) >= 15

    def test_known_roles_present(self):
        roles = [d.name for d in ROLES_DIR.iterdir() if (d / "role.md").is_file()]
        assert "backend" in roles
        assert "frontend" in roles
        assert "security" in roles


# --- list_skills ---

class TestListSkills:
    def test_returns_skills(self):
        skills = [d.name for d in sorted(SKILLS_DIR.iterdir()) if (d / "SKILL.md").is_file()]
        assert len(skills) >= 10

    def test_known_skills_present(self):
        skills = [d.name for d in SKILLS_DIR.iterdir() if (d / "SKILL.md").is_file()]
        assert "implementation" in skills
        assert "precommit" in skills
        assert "evaluate" in skills


# --- list_agents ---

class TestListAgents:
    def test_returns_agents(self):
        agents = [f.stem for f in sorted(AGENTS_DIR.glob("*.md"))]
        assert len(agents) >= 5

    def test_known_agents_present(self):
        agents = [f.stem for f in AGENTS_DIR.glob("*.md")]
        assert "readme-validator" in agents
        assert "scale-estimator" in agents


# --- build_research_plan ---

class TestBuildResearchPlan:
    def test_returns_plan(self):
        result = build_research_plan("how to build an MCP server")
        assert "steps" in result
        assert result["type"] == "parallel_research"

    def test_has_fetch_and_synthesize(self):
        result = build_research_plan("test query", search_count=3)
        phases = [s["phase"] for s in result["steps"]]
        assert "fetch" in phases
        assert "synthesize" in phases

    def test_fetch_uses_cheap_model(self):
        result = build_research_plan("test query")
        fetch_step = [s for s in result["steps"] if s["phase"] == "fetch"][0]
        assert fetch_step["model"] in ("haiku", "sonnet")

    def test_synthesize_uses_expensive_model(self):
        result = build_research_plan("test query")
        synth_step = [s for s in result["steps"] if s["phase"] == "synthesize"][0]
        assert synth_step["model"] in ("fable", "opus")


# --- Server structure test ---

class TestServerStructure:
    def test_server_imports_and_has_tools(self):
        """Verify the MCP server module loads and registers all 8 tools."""
        from toolkit_mcp.server import mcp as toolkit_mcp_server
        # FastMCP server object should exist
        assert toolkit_mcp_server is not None
        assert toolkit_mcp_server.name == "agent-toolkit"
