#!/usr/bin/env python3
"""Tests for roles/orchestrator.py — cross-role invocation and multi-agent routing."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "roles"))


def _create_role(roles_dir, name, invokes=None, cost_guidance=None):
    """Helper: create a minimal role.md with invokes config."""
    role_dir = roles_dir / name
    role_dir.mkdir(parents=True, exist_ok=True)

    invokes_yaml = ""
    if invokes:
        lines = []
        for key, roles in invokes.items():
            lines.append(f"  {key}: {json.dumps(roles)}")
        invokes_yaml = "invokes:\n" + "\n".join(lines)

    cost_yaml = ""
    if cost_guidance:
        lines = []
        for tier, tasks in cost_guidance.items():
            lines.append(f"  {tier}: {json.dumps(tasks)}")
        cost_yaml = "cost_guidance:\n" + "\n".join(lines)

    (role_dir / "role.md").write_text(
        f"---\nname: {name}\nscope: test\n{invokes_yaml}\n{cost_yaml}\n---\n\n## Advisory\n\nRole {name}.\n"
    )


class TestGetInvocations:
    def test_returns_after_skeleton_roles(self, tmp_path):
        from orchestrator import get_invocations

        _create_role(tmp_path, "backend", invokes={
            "after_skeleton": ["dba", "security"],
            "for_evaluation": ["qa", "production"],
        })

        result = get_invocations("backend", "after_skeleton", roles_dir=tmp_path)
        assert result == ["dba", "security"]

    def test_returns_evaluation_roles(self, tmp_path):
        from orchestrator import get_invocations

        _create_role(tmp_path, "backend", invokes={
            "after_skeleton": ["dba"],
            "for_evaluation": ["security", "qa"],
        })

        result = get_invocations("backend", "for_evaluation", roles_dir=tmp_path)
        assert result == ["security", "qa"]

    def test_returns_empty_for_unknown_phase(self, tmp_path):
        from orchestrator import get_invocations

        _create_role(tmp_path, "backend", invokes={"after_skeleton": ["dba"]})

        result = get_invocations("backend", "after_deployment", roles_dir=tmp_path)
        assert result == []

    def test_returns_empty_when_no_invokes(self, tmp_path):
        from orchestrator import get_invocations

        _create_role(tmp_path, "frontend")

        result = get_invocations("frontend", "after_skeleton", roles_dir=tmp_path)
        assert result == []

    def test_returns_empty_when_role_missing(self, tmp_path):
        from orchestrator import get_invocations

        result = get_invocations("nonexistent", "after_skeleton", roles_dir=tmp_path)
        assert result == []


class TestGetModelTier:
    def test_cheap_task(self, tmp_path):
        from orchestrator import get_model_tier

        _create_role(tmp_path, "backend", cost_guidance={
            "cheap": ["file-search", "lint"],
            "mid": ["code-generation"],
            "expensive": ["architecture-decision"],
        })

        assert get_model_tier("backend", "file-search", roles_dir=tmp_path) == "cheap"
        assert get_model_tier("backend", "lint", roles_dir=tmp_path) == "cheap"

    def test_expensive_task(self, tmp_path):
        from orchestrator import get_model_tier

        _create_role(tmp_path, "backend", cost_guidance={
            "cheap": ["lint"],
            "expensive": ["architecture-decision"],
        })

        assert get_model_tier("backend", "architecture-decision", roles_dir=tmp_path) == "expensive"

    def test_unknown_task_defaults_to_mid(self, tmp_path):
        from orchestrator import get_model_tier

        _create_role(tmp_path, "backend", cost_guidance={
            "cheap": ["lint"],
        })

        assert get_model_tier("backend", "unknown-task", roles_dir=tmp_path) == "mid"

    def test_no_cost_guidance_defaults_to_mid(self, tmp_path):
        from orchestrator import get_model_tier

        _create_role(tmp_path, "frontend")

        assert get_model_tier("frontend", "anything", roles_dir=tmp_path) == "mid"


class TestBuildOrchestrationPlan:
    def test_new_feature_plan(self, tmp_path):
        from orchestrator import build_orchestration_plan

        _create_role(tmp_path, "backend", invokes={
            "after_skeleton": ["dba", "security"],
            "for_evaluation": ["qa", "production"],
        })

        plan = build_orchestration_plan(
            primary_role="backend",
            task_type="new_feature",
            active_roles=["backend", "dba", "security", "qa", "production"],
            roles_dir=tmp_path,
        )

        assert plan["primary"] == "backend"
        assert plan["task_type"] == "new_feature"
        assert len(plan["steps"]) >= 3
        # Should have: build, evaluate_after_skeleton, evaluate_final
        step_types = [s["type"] for s in plan["steps"]]
        assert "build" in step_types
        assert "evaluate" in step_types

    def test_bug_fix_plan(self, tmp_path):
        from orchestrator import build_orchestration_plan

        _create_role(tmp_path, "backend", invokes={
            "for_evaluation": ["security", "qa"],
        })

        plan = build_orchestration_plan(
            primary_role="backend",
            task_type="bug_fix",
            active_roles=["backend", "security", "qa"],
            roles_dir=tmp_path,
        )

        step_types = [s["type"] for s in plan["steps"]]
        assert "fix" in step_types
        assert "evaluate" in step_types

    def test_only_includes_active_roles(self, tmp_path):
        from orchestrator import build_orchestration_plan

        _create_role(tmp_path, "backend", invokes={
            "after_skeleton": ["dba", "security", "infrastructure"],
            "for_evaluation": ["qa", "production"],
        })

        plan = build_orchestration_plan(
            primary_role="backend",
            task_type="new_feature",
            active_roles=["backend", "dba", "qa"],  # security, infra, production NOT active
            roles_dir=tmp_path,
        )

        # Should only include roles that are actually active
        all_roles_in_plan = set()
        for step in plan["steps"]:
            all_roles_in_plan.update(step.get("roles", []))
            if "role" in step:
                all_roles_in_plan.add(step["role"])

        assert "infrastructure" not in all_roles_in_plan
        assert "production" not in all_roles_in_plan


class TestExtractRoleChecklist:
    def test_extract_role_checklist_anti_patterns(self, tmp_path):
        from orchestrator import _extract_role_checklist

        role_dir = tmp_path / "backend"
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / "role.md").write_text(
            "---\nname: backend\n---\n\n"
            "## Anti-Patterns (flag these)\n\n"
            "- N+1 queries\n"
            "- Missing pagination\n\n"
            "## Quality Checks\n\n"
            "- [ ] Input validation\n"
            "- [ ] Parameterized queries\n"
        )
        result = _extract_role_checklist("backend", roles_dir=tmp_path)
        assert "N+1 queries" in result["anti_patterns"]
        assert "Missing pagination" in result["anti_patterns"]
        assert "Input validation" in result["quality_checks"]
        assert "Parameterized queries" in result["quality_checks"]

    def test_empty_when_no_sections(self, tmp_path):
        from orchestrator import _extract_role_checklist

        role_dir = tmp_path / "minimal"
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / "role.md").write_text("---\nname: minimal\n---\n\n## Advisory\n\nJust text.\n")
        result = _extract_role_checklist("minimal", roles_dir=tmp_path)
        assert result["anti_patterns"] == []
        assert result["quality_checks"] == []

    def test_empty_when_role_missing(self, tmp_path):
        from orchestrator import _extract_role_checklist

        result = _extract_role_checklist("nonexistent", roles_dir=tmp_path)
        assert result["anti_patterns"] == []
        assert result["quality_checks"] == []


class TestPlanToContext:
    def test_generates_readable_context(self, tmp_path):
        from orchestrator import build_orchestration_plan, plan_to_context

        _create_role(tmp_path, "backend", invokes={
            "after_skeleton": ["dba"],
            "for_evaluation": ["security"],
        })

        plan = build_orchestration_plan(
            primary_role="backend",
            task_type="new_feature",
            active_roles=["backend", "dba", "security"],
            roles_dir=tmp_path,
        )

        context = plan_to_context(plan)
        assert "ORCHESTRATION PLAN" in context
        assert "backend" in context
        assert "Step" in context

    def test_plan_to_context_includes_anti_patterns(self, tmp_path):
        """Build steps must inject the role's anti-patterns as a pre-flight checklist."""
        from orchestrator import build_orchestration_plan, plan_to_context

        role_dir = tmp_path / "backend"
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / "role.md").write_text(
            "---\nname: backend\nscope: test\n"
            "invokes:\n  after_skeleton: [\"dba\"]\n---\n\n"
            "## Anti-Patterns (flag these)\n\n"
            "- N+1 queries — use eager loading\n"
            "- Missing pagination on list endpoints\n"
            "- Raw SQL string concatenation\n\n"
            "## Quality Checks\n\n"
            "- [ ] All endpoints have input validation\n"
            "- [ ] Pagination on all list endpoints\n"
            "- [ ] Database queries are parameterized\n"
        )
        _create_role(tmp_path, "dba")

        plan = build_orchestration_plan(
            primary_role="backend",
            task_type="new_feature",
            active_roles=["backend", "dba"],
            roles_dir=tmp_path,
        )
        context = plan_to_context(plan)

        # Anti-patterns must appear in the build step
        assert "N+1 queries" in context
        assert "Missing pagination" in context
        # Quality checks must appear
        assert "input validation" in context
        assert "parameterized" in context

    def test_build_step_labels_checklist(self, tmp_path):
        """Build step checklist must be clearly labeled so agent can't miss it."""
        from orchestrator import build_orchestration_plan, plan_to_context

        role_dir = tmp_path / "backend"
        role_dir.mkdir(parents=True, exist_ok=True)
        (role_dir / "role.md").write_text(
            "---\nname: backend\nscope: test\n---\n\n"
            "## Anti-Patterns (flag these)\n\n"
            "- God controller\n\n"
            "## Quality Checks\n\n"
            "- [ ] Health check endpoint exists\n"
        )

        plan = build_orchestration_plan(
            primary_role="backend",
            task_type="new_feature",
            active_roles=["backend"],
            roles_dir=tmp_path,
        )
        context = plan_to_context(plan)

        assert "MUST NOT" in context or "DO NOT" in context or "NEVER" in context
        assert "MUST" in context
