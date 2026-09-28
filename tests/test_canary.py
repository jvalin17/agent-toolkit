"""Tests for canary context-loss detection.

Covers:
- session_init injects canary instruction when gates.json has "canary" field
- canary_check.py detects missing canary in assistant output
- canary_check.py passes when canary is present
- no check when canary is not configured
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))

from hooks.session_init import build_context, load_session_config
from canary_check import check_canary_in_text, run_canary_check


# --- session_init: canary injection ---


class TestCanaryInjection:
    def test_build_context_includes_canary_instruction(self):
        """When canary is set, build_context injects the instruction."""
        context = build_context(
            files=[], report_count=0, warnings=[], continuation=None,
            canary="Jean",
        )
        assert "Jean" in context
        assert "Start every response with" in context

    def test_build_context_no_canary_when_empty(self):
        """When canary is empty/None, no canary instruction appears."""
        context = build_context(
            files=[], report_count=0, warnings=[], continuation=None,
            canary="",
        )
        assert "Start every response with" not in context

    def test_build_context_no_canary_when_absent(self):
        """When canary kwarg is not provided, no canary instruction."""
        context = build_context(
            files=[], report_count=0, warnings=[], continuation=None,
        )
        assert "Start every response with" not in context

    def test_load_session_config_reads_canary(self, tmp_path):
        """load_session_config returns canary from gates.json."""
        gates = {"mode": "default", "canary": "Boss"}
        (tmp_path / "gates.json").write_text(json.dumps(gates))
        config = load_session_config(tmp_path)
        assert config["canary"] == "Boss"

    def test_load_session_config_default_canary_hey(self, tmp_path):
        """load_session_config returns 'Hey' as default canary when not set."""
        gates = {"mode": "default"}
        (tmp_path / "gates.json").write_text(json.dumps(gates))
        config = load_session_config(tmp_path)
        assert config["canary"] == "Hey"


# --- canary_check: detection logic ---


class TestCanaryDetection:
    def test_canary_present_at_start(self):
        """Returns None when canary word is at the start of text."""
        result = check_canary_in_text("Jean, here's what I found...", "Jean")
        assert result is None

    def test_canary_missing(self):
        """Returns warning when canary is missing from text."""
        result = check_canary_in_text("Here's what I found...", "Jean")
        assert result is not None
        assert "context" in result.lower() or "session" in result.lower()

    def test_canary_present_case_insensitive(self):
        """Canary check is case-insensitive."""
        result = check_canary_in_text("jean, let me check that.", "Jean")
        assert result is None

    def test_canary_present_with_punctuation(self):
        """Canary followed by comma or colon still matches."""
        assert check_canary_in_text("Jean: here's the fix.", "Jean") is None
        assert check_canary_in_text("Jean! Done.", "Jean") is None

    def test_empty_canary_always_passes(self):
        """Empty canary means feature is off — always passes."""
        result = check_canary_in_text("anything here", "")
        assert result is None

    def test_empty_text_with_canary_set(self):
        """Empty assistant text with canary set — no false alarm."""
        result = check_canary_in_text("", "Jean")
        assert result is None

    def test_canary_not_at_start(self):
        """Canary appearing mid-text (not at start) should warn."""
        result = check_canary_in_text("Let me check. Jean would say...", "Jean")
        assert result is not None


# --- canary_check: hook integration ---


class TestCanaryHookIntegration:
    def test_run_canary_check_no_canary_configured(self, tmp_path):
        """No canary in gates.json → no check, exit 0."""
        gates = {"mode": "default"}
        (tmp_path / "gates.json").write_text(json.dumps(gates))
        with patch("canary_check.load_gate_config", return_value=gates):
            with patch("canary_check.find_latest_session_log", return_value=None):
                exit_code, output = run_canary_check("{}")
        assert exit_code == 0
        assert output == ""

    def test_run_canary_check_canary_present(self, tmp_path):
        """Canary present in assistant text → no warning."""
        gates = {"canary": "Boss"}
        log_path = tmp_path / "session.jsonl"
        log_path.write_text(
            json.dumps({"type": "assistant", "message": {"content": "Boss, here's the result."}}) + "\n"
        )
        with patch("canary_check.load_gate_config", return_value=gates):
            with patch("canary_check.get_config_value", side_effect=lambda c, k, d="": c.get(k, d)):
                with patch("canary_check.find_latest_session_log", return_value=log_path):
                    exit_code, output = run_canary_check("{}")
        assert exit_code == 0
        assert output == ""

    def test_run_canary_check_canary_missing(self, tmp_path):
        """Canary missing from assistant text → injects suggestion."""
        gates = {"canary": "Boss"}
        log_path = tmp_path / "session.jsonl"
        log_path.write_text(
            json.dumps({"type": "assistant", "message": {"content": "Here's the result."}}) + "\n"
        )
        with patch("canary_check.load_gate_config", return_value=gates):
            with patch("canary_check.get_config_value", side_effect=lambda c, k, d="": c.get(k, d)):
                with patch("canary_check.find_latest_session_log", return_value=log_path):
                    exit_code, output = run_canary_check("{}")
        assert exit_code == 0
        assert output != ""
        parsed = json.loads(output)
        context = parsed["hookSpecificOutput"]["additionalContext"]
        assert "context" in context.lower() or "session" in context.lower()
