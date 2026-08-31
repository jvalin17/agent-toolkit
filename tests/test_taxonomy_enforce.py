#!/usr/bin/env python3
"""Tests for hooks/taxonomy_enforce.py — model tier enforcement."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))


class TestDetectTaskTier:
    def test_file_search_is_cheap(self):
        from taxonomy_enforce import detect_task_tier
        assert detect_task_tier("search for all Python files") == "cheap"
        assert detect_task_tier("find file matching pattern") == "cheap"
        assert detect_task_tier("lint check on src/") == "cheap"

    def test_architecture_is_expensive(self):
        from taxonomy_enforce import detect_task_tier
        assert detect_task_tier("design system architecture") == "expensive"
        assert detect_task_tier("security audit of auth module") == "expensive"
        assert detect_task_tier("synthesize findings from reviews") == "expensive"

    def test_code_generation_is_mid(self):
        from taxonomy_enforce import detect_task_tier
        assert detect_task_tier("implement user registration") == "mid"
        assert detect_task_tier("build the API endpoint") == "mid"


class TestCheckModelMatch:
    def test_no_model_on_vague_task_blocks(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("", "mid")
        assert result["block"] is True
        assert "model" in result["reason"].lower()

    def test_no_model_on_cheap_blocks(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("", "cheap")
        assert result["block"] is True

    def test_no_model_on_expensive_blocks(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("", "expensive")
        assert result["block"] is True

    def test_expensive_on_cheap_blocks(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("opus", "cheap")
        assert result["block"] is True
        assert "Expensive" in result["reason"]

    def test_cheap_on_expensive_blocks(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("haiku", "expensive")
        assert result["block"] is True
        assert "Cheap" in result["reason"]

    def test_matching_tier_ok(self):
        from taxonomy_enforce import check_model_match
        assert check_model_match("haiku", "cheap")["block"] is False
        assert check_model_match("sonnet", "mid")["block"] is False
        assert check_model_match("opus", "expensive")["block"] is False

    def test_sonnet_on_cheap_ok(self):
        from taxonomy_enforce import check_model_match
        # sonnet on cheap is not ideal but not a violation
        assert check_model_match("sonnet", "cheap")["block"] is False

    def test_sonnet_on_expensive_ok(self):
        from taxonomy_enforce import check_model_match
        # sonnet on expensive is not ideal but acceptable as fallback
        assert check_model_match("sonnet", "expensive")["block"] is False


class TestTddInjection:
    """PreToolUse Agent hook injects TDD instructions into implementation prompts."""

    def test_implementation_prompt_gets_tdd_context(self):
        from taxonomy_enforce import get_tdd_injection

        result = get_tdd_injection("implement user registration feature")
        assert result is not None
        assert "failing test" in result.lower()
        assert "before" in result.lower()

    def test_search_prompt_no_tdd_context(self):
        from taxonomy_enforce import get_tdd_injection

        result = get_tdd_injection("search for all Python test files")
        assert result is None

    def test_fix_prompt_gets_tdd_context(self):
        from taxonomy_enforce import get_tdd_injection

        result = get_tdd_injection("fix the login bug in auth module")
        assert result is not None
        assert "failing test" in result.lower()

    def test_review_prompt_no_tdd_context(self):
        from taxonomy_enforce import get_tdd_injection

        result = get_tdd_injection("review code quality and security")
        assert result is None

    def test_build_prompt_gets_tdd_context(self):
        from taxonomy_enforce import get_tdd_injection

        result = get_tdd_injection("build the API endpoint for users")
        assert result is not None
