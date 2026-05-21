#!/usr/bin/env python3
"""Tests for route_to_skill.py — intent detection and skill routing."""

import json
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from route_to_skill import run_route_to_skill  # noqa: E402


def make_input(prompt: str) -> str:
    return json.dumps({"prompt": prompt})


def parse_context(output: str) -> str:
    data = json.loads(output)
    return data["hookSpecificOutput"]["additionalContext"]


class TestSlashCommandsBypass:
    """Prompts starting with / should never be routed."""

    @pytest.mark.parametrize("prompt", [
        "/precommit", "/evaluate", "/implementation build a thing",
        "/debug fix the crash", "/status",
    ])
    def test_slash_commands_ignored(self, tmp_path, prompt):
        exit_code, output = run_route_to_skill(make_input(prompt), tmp_path)
        assert exit_code == 0
        assert output == ""


class TestBugFixRouting:
    @pytest.mark.parametrize("prompt", [
        "fix the bug in gate.py",
        "the login is broken",
        "app crashes on startup",
        "this is not working",
        "fix the error in the parser",
        "getting an error when I submit",
        "blank page after login",
        "0 results returned from search",
    ])
    def test_debug_routing(self, tmp_path, prompt):
        _, output = run_route_to_skill(make_input(prompt), tmp_path)
        context = parse_context(output)
        assert "/debug" in context

    def test_fix_the_design_not_routed_to_debug(self, tmp_path):
        """'fix the design' is not a bug — should NOT route to debug."""
        _, output = run_route_to_skill(make_input("fix the design of the homepage"), tmp_path)
        # Should not contain /debug routing
        if output:
            context = parse_context(output)
            assert "/debug" not in context


class TestBuildRouting:
    @pytest.mark.parametrize("prompt", [
        "build a recipe finder app",
        "implement the search feature",
        "create a new API endpoint",
        "add a feature for user profiles",
        "scaffold the new module",
        "make a CLI tool for linting",
    ])
    def test_implementation_routing(self, tmp_path, prompt):
        _, output = run_route_to_skill(make_input(prompt), tmp_path)
        context = parse_context(output)
        assert "/implementation" in context


class TestRefactorRouting:
    @pytest.mark.parametrize("prompt", [
        "refactor the auth module",
        "clean up the database code",
        "restructure the project layout",
        "simplify the code in utils.py",
    ])
    def test_refactor_routing(self, tmp_path, prompt):
        _, output = run_route_to_skill(make_input(prompt), tmp_path)
        context = parse_context(output)
        assert "/implementation" in context
        assert "refactor" in context.lower()


class TestExploreRouting:
    @pytest.mark.parametrize("prompt", [
        "how does the auth system work",
        "explore the codebase",
        "what does this project do",
        "walk me through the API layer",
    ])
    def test_explore_routing(self, tmp_path, prompt):
        _, output = run_route_to_skill(make_input(prompt), tmp_path)
        context = parse_context(output)
        assert "/explore" in context


class TestReviewRouting:
    @pytest.mark.parametrize("prompt", [
        "review the code changes",
        "check the quality of this PR",
        "evaluate the architecture",
        "how good is the test coverage",
    ])
    def test_review_routing(self, tmp_path, prompt):
        _, output = run_route_to_skill(make_input(prompt), tmp_path)
        assert output != ""  # Some quality skill should be suggested


class TestSetupRouting:
    @pytest.mark.parametrize("prompt", [
        "set up the project environment",
        "create a Dockerfile",
        "configure CI/CD pipeline",
    ])
    def test_setup_routing(self, tmp_path, prompt):
        _, output = run_route_to_skill(make_input(prompt), tmp_path)
        context = parse_context(output)
        assert "/setup" in context


class TestRequirementsRouting:
    @pytest.mark.parametrize("prompt", [
        "gather requirements for the new feature",
        "plan the project scope",
        "what should we build for the MVP",
    ])
    def test_requirements_routing(self, tmp_path, prompt):
        _, output = run_route_to_skill(make_input(prompt), tmp_path)
        context = parse_context(output)
        assert "/requirements" in context


class TestArchitectureRouting:
    @pytest.mark.parametrize("prompt", [
        "design the system architecture",
        "which database should we use",
        "choose between REST and GraphQL",
    ])
    def test_architecture_routing(self, tmp_path, prompt):
        _, output = run_route_to_skill(make_input(prompt), tmp_path)
        context = parse_context(output)
        assert "/architecture" in context


class TestNoMatch:
    @pytest.mark.parametrize("prompt", [
        "hello",
        "thanks",
        "what time is it",
        "commit this",
    ])
    def test_unmatched_prompts_pass_through(self, tmp_path, prompt):
        exit_code, output = run_route_to_skill(make_input(prompt), tmp_path)
        assert exit_code == 0
        assert output == ""


class TestEdgeCases:
    def test_empty_input(self, tmp_path):
        exit_code, output = run_route_to_skill("", tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_invalid_json(self, tmp_path):
        exit_code, output = run_route_to_skill("bad", tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_missing_prompt_field(self, tmp_path):
        exit_code, output = run_route_to_skill(json.dumps({}), tmp_path)
        assert exit_code == 0
        assert output == ""

    def test_case_insensitive(self, tmp_path):
        _, output = run_route_to_skill(make_input("FIX THE BUG"), tmp_path)
        context = parse_context(output)
        assert "/debug" in context
