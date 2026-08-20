#!/usr/bin/env python3
"""Tests for roles/agent_taxonomy.py — model selection for tasks."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "roles"))


class TestSelectAgent:
    def test_fetch_selects_haiku(self):
        from agent_taxonomy import select_agent
        result = select_agent("fetch")
        assert result["model"] == "haiku"

    def test_code_generation_selects_sonnet(self):
        from agent_taxonomy import select_agent
        result = select_agent("code_generation")
        assert result["model"] == "sonnet"

    def test_architecture_selects_fable_or_opus(self):
        from agent_taxonomy import select_agent
        result = select_agent("architecture_decision")
        assert result["model"] in ("fable", "opus")

    def test_synthesize_selects_fable_or_opus(self):
        from agent_taxonomy import select_agent
        result = select_agent("synthesize")
        assert result["model"] in ("fable", "opus")

    def test_fallback_when_preferred_unavailable(self):
        from agent_taxonomy import select_agent
        # Only sonnet available, but synthesize prefers fable/opus
        result = select_agent("synthesize", available=["sonnet"])
        assert result["model"] == "sonnet"
        assert "fallback" in result["reason"]

    def test_haiku_fallback_for_fetch_when_only_sonnet(self):
        from agent_taxonomy import select_agent
        result = select_agent("fetch", available=["sonnet"])
        assert result["model"] == "sonnet"

    def test_unknown_task_defaults_to_sonnet(self):
        from agent_taxonomy import select_agent
        result = select_agent("unknown_task_xyz")
        assert result["model"] == "sonnet"
        assert "unknown" in result["reason"]

    def test_returns_model_id(self):
        from agent_taxonomy import select_agent
        result = select_agent("fetch")
        assert "model_id" in result
        assert "claude" in result["model_id"]

    def test_returns_max_tokens(self):
        from agent_taxonomy import select_agent
        result = select_agent("fetch")
        assert result["max_tokens"] == 1000  # fetch is small

        result = select_agent("code_generation")
        assert result["max_tokens"] == 4000  # code gen is larger

    def test_security_audit_prefers_expensive(self):
        from agent_taxonomy import select_agent
        result = select_agent("security_audit")
        assert result["model"] in ("fable", "opus")

    def test_lint_check_prefers_cheap(self):
        from agent_taxonomy import select_agent
        result = select_agent("lint_check")
        assert result["model"] == "haiku"


class TestBuildResearchPlan:
    def test_returns_two_phases(self):
        from agent_taxonomy import build_research_plan
        plan = build_research_plan("how does auth work")
        assert len(plan["steps"]) == 2
        assert plan["steps"][0]["phase"] == "fetch"
        assert plan["steps"][1]["phase"] == "synthesize"

    def test_fetch_phase_is_parallel(self):
        from agent_taxonomy import build_research_plan
        plan = build_research_plan("test", search_count=3)
        fetch = plan["steps"][0]
        assert fetch["parallel"] is True
        assert fetch["agent_count"] == 3

    def test_synthesize_is_not_parallel(self):
        from agent_taxonomy import build_research_plan
        plan = build_research_plan("test")
        synth = plan["steps"][1]
        assert synth["parallel"] is False
        assert synth["agent_count"] == 1

    def test_fetch_uses_cheaper_model(self):
        from agent_taxonomy import build_research_plan
        plan = build_research_plan("test")
        fetch_model = plan["steps"][0]["model"]
        synth_model = plan["steps"][1]["model"]
        # Fetch should be cheaper or same as synthesize
        tier_order = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}
        assert tier_order.get(fetch_model, 1) <= tier_order.get(synth_model, 2)

    def test_respects_available_models(self):
        from agent_taxonomy import build_research_plan
        plan = build_research_plan("test", available=["sonnet"])
        assert plan["steps"][0]["model"] == "sonnet"
        assert plan["steps"][1]["model"] == "sonnet"
