#!/usr/bin/env python3
"""Tests for the MCP server — zero dependencies, tests tool functions + protocol."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ROLES_DIR = ROOT / "roles"
SKILLS_DIR = ROOT / "skills"
AGENTS_DIR = ROOT / "agents"
sys.path.insert(0, str(ROLES_DIR))
sys.path.insert(0, str(ROOT / "toolkit_mcp"))

from server import TOOLS, process_message


# --- Tool functions ---

class TestSelectAgent:
    def test_fetch_returns_haiku(self):
        result = TOOLS["select_agent"]["fn"]({"task_type": "fetch"})
        assert result["model"] == "haiku"

    def test_architecture_returns_expensive(self):
        result = TOOLS["select_agent"]["fn"]({"task_type": "architecture_decision"})
        assert result["model"] in ("fable", "opus")

    def test_unknown_type_returns_sonnet(self):
        result = TOOLS["select_agent"]["fn"]({"task_type": "completely_made_up"})
        assert result["model"] == "sonnet"

    def test_with_limited_available(self):
        result = TOOLS["select_agent"]["fn"]({"task_type": "fetch", "available": ["sonnet"]})
        assert result["model"] == "sonnet"


class TestBuildPlan:
    def test_new_feature_returns_steps(self):
        result = TOOLS["build_plan"]["fn"]({"primary_role": "backend", "task_type": "new_feature", "active_roles": ["backend", "security"]})
        assert "steps" in result
        assert len(result["steps"]) > 0

    def test_new_feature_includes_skills(self):
        result = TOOLS["build_plan"]["fn"]({"primary_role": "backend", "task_type": "new_feature", "active_roles": ["backend", "security"]})
        skill_names = [s.get("skill") for s in result["steps"] if s.get("type") == "skill"]
        assert "requirements" in skill_names
        assert "reviewer" in skill_names
        assert "evaluate" in skill_names
        assert "precommit" in skill_names

    def test_bug_fix_uses_debug_tool(self):
        result = TOOLS["build_plan"]["fn"]({"primary_role": "backend", "task_type": "bug_fix", "active_roles": ["backend"]})
        skill_names = [s.get("skill") for s in result["steps"] if s.get("type") == "skill"]
        assert "debug_tool" in skill_names


class TestPlanToText:
    def test_renders_plan(self):
        plan = TOOLS["build_plan"]["fn"]({"primary_role": "backend", "task_type": "new_feature", "active_roles": ["backend"]})
        text = TOOLS["plan_to_text"]["fn"]({"plan": plan})
        assert "ORCHESTRATION PLAN" in text
        assert "haiku" in text
        assert "opus" in text


class TestGetRoleContext:
    def test_with_project_dir(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text('{"dependencies": {"express": "^4.0.0"}}')
        result = TOOLS["get_role_context"]["fn"]({"project_dir": str(tmp_path)})
        assert isinstance(result, dict)

    def test_nonexistent_dir_returns_error(self):
        result = TOOLS["get_role_context"]["fn"]({"project_dir": "/nonexistent/path"})
        assert "error" in result

    def test_with_explicit_roles(self, tmp_path):
        result = TOOLS["get_role_context"]["fn"]({"project_dir": str(tmp_path), "roles": ["backend", "security"]})
        assert isinstance(result, dict)


class TestListRoles:
    def test_returns_roles(self):
        roles = TOOLS["list_roles"]["fn"]({})
        assert len(roles) >= 15
        names = [r["name"] for r in roles]
        assert "backend" in names
        assert "security" in names


class TestListSkills:
    def test_returns_skills(self):
        skills = TOOLS["list_skills"]["fn"]({})
        assert len(skills) >= 10
        names = [s["name"] for s in skills]
        assert "implementation" in names
        assert "precommit" in names


class TestListAgents:
    def test_returns_agents(self):
        agents = TOOLS["list_agents"]["fn"]({})
        assert len(agents) >= 5
        names = [a["name"] for a in agents]
        assert "readme-validator" in names


class TestBuildResearchPlan:
    def test_returns_plan(self):
        result = TOOLS["build_research_plan"]["fn"]({"query": "MCP server patterns"})
        assert result["type"] == "parallel_research"
        phases = [s["phase"] for s in result["steps"]]
        assert "fetch" in phases
        assert "synthesize" in phases

    def test_synthesize_uses_expensive_model(self):
        result = TOOLS["build_research_plan"]["fn"]({"query": "test", "search_count": 3})
        synth = [s for s in result["steps"] if s["phase"] == "synthesize"][0]
        assert synth["model"] in ("fable", "opus")


# --- JSON-RPC protocol ---

class TestProtocol:
    def test_initialize(self):
        resp = process_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["result"]["serverInfo"]["name"] == "agent-toolkit"

    def test_tools_list(self):
        resp = process_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        tools = resp["result"]["tools"]
        assert len(tools) == 8
        names = [t["name"] for t in tools]
        assert "select_agent" in names
        assert "build_plan" in names

    def test_tools_call(self):
        resp = process_message({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "select_agent", "arguments": {"task_type": "fetch"}
        }})
        content = json.loads(resp["result"]["content"][0]["text"])
        assert content["model"] == "haiku"

    def test_unknown_tool(self):
        resp = process_message({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
            "name": "nonexistent", "arguments": {}
        }})
        assert resp["result"]["isError"] is True

    def test_unknown_method(self):
        resp = process_message({"jsonrpc": "2.0", "id": 5, "method": "foo/bar", "params": {}})
        assert resp["error"]["code"] == -32601

    def test_notification_no_response(self):
        resp = process_message({"jsonrpc": "2.0", "method": "initialized", "params": {}})
        assert resp is None
