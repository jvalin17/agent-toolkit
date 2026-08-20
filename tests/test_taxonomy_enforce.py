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
    def test_no_model_on_vague_task_ok(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("", "mid")
        assert result["warn"] is False

    def test_no_model_on_cheap_suggests(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("", "cheap")
        assert result["warn"] is False
        assert "haiku" in result.get("suggestion", "")

    def test_expensive_on_cheap_warns(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("opus", "cheap")
        assert result["warn"] is True
        assert "Expensive" in result["message"]

    def test_cheap_on_expensive_warns(self):
        from taxonomy_enforce import check_model_match
        result = check_model_match("haiku", "expensive")
        assert result["warn"] is True
        assert "Cheap" in result["message"]

    def test_matching_tier_ok(self):
        from taxonomy_enforce import check_model_match
        assert check_model_match("haiku", "cheap")["warn"] is False
        assert check_model_match("sonnet", "mid")["warn"] is False
        assert check_model_match("opus", "expensive")["warn"] is False

    def test_sonnet_on_cheap_ok(self):
        from taxonomy_enforce import check_model_match
        # sonnet on cheap is not ideal but not a violation
        assert check_model_match("sonnet", "cheap")["warn"] is False

    def test_sonnet_on_expensive_ok(self):
        from taxonomy_enforce import check_model_match
        # sonnet on expensive is not ideal but acceptable as fallback
        assert check_model_match("sonnet", "expensive")["warn"] is False
