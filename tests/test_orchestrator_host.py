"""Orchestrator attaches host config + pull_policy (LLM-agnostic modular)."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "roles"))
sys.path.insert(0, str(ROOT / "hooks"))


def test_plan_includes_host_and_pull_policy_for_cursor():
    from orchestrator import build_orchestration_plan, plan_to_context

    with patch.dict(os.environ, {"AGENT_TOOLKIT_TOOL": "cursor"}, clear=True):
        plan = build_orchestration_plan(
            primary_role="backend",
            task_type="bug_fix",
            active_roles=["backend", "qa"],
            roles_dir=ROOT / "roles",
        )
    assert "host" in plan
    assert plan["host"]["id"] == "cursor"
    assert "pull_policy" in plan
    assert plan["pull_policy"]["skills"] == "stub_first"
    assert "check_tdd_order" in plan["pull_policy"]["functions"]
    assert "bootstrap_preview" in plan
    assert len(plan["bootstrap_preview"]) > 20

    text = plan_to_context(plan, roles_dir=ROOT / "roles")
    assert "HOST:" in text or "cursor" in text.lower()
    assert "pull" in text.lower() or "stub_first" in text


def test__attach_host_context_adds_keys():
    """Covers _attach_host_context via public plan builder."""
    from orchestrator import _attach_host_context

    with patch.dict(os.environ, {"AGENT_TOOLKIT_TOOL": "gemini"}, clear=True):
        plan = _attach_host_context(
            {"primary": "backend", "task_type": "bug_fix", "active_roles": [], "steps": []}
        )
    assert plan["host"]["id"] == "gemini"
    assert plan["pull_policy"]["skills"] == "stub_first"
    assert "bootstrap_preview" in plan


def test_plan_claude_host_when_overridden():
    from orchestrator import build_orchestration_plan

    with patch.dict(os.environ, {"AGENT_TOOLKIT_TOOL": "claude-code"}, clear=True):
        plan = build_orchestration_plan(
            primary_role="backend",
            task_type="bug_fix",
            active_roles=["backend"],
            roles_dir=ROOT / "roles",
        )
    assert plan["host"]["id"] == "claude-code"
    assert plan["host"]["stamp_mode"] == "hook_skill_passed"
