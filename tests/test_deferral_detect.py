"""Tests for deferral_detect.py — anti-deferral hook."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))

from deferral_detect import (
    DEFERRAL_PATTERNS,
    extract_last_assistant_text,
    detect_deferral,
    run_deferral_check,
)


# --- extract_last_assistant_text ---


class TestExtractLastAssistantText:
    def test_returns_text_from_last_assistant_message(self, tmp_path):
        log = tmp_path / "session.jsonl"
        log.write_text(
            json.dumps({"type": "human", "message": {"content": "do the work"}}) + "\n"
            + json.dumps({
                "type": "assistant",
                "message": {"content": [
                    {"type": "text", "text": "I'll start a new session for this."}
                ]}
            }) + "\n"
        )
        assert "new session" in extract_last_assistant_text(log)

    def test_returns_string_content(self, tmp_path):
        log = tmp_path / "session.jsonl"
        log.write_text(
            json.dumps({
                "type": "assistant",
                "message": {"content": "Let me defer this to next time."}
            }) + "\n"
        )
        assert "defer" in extract_last_assistant_text(log)

    def test_returns_empty_when_no_assistant(self, tmp_path):
        log = tmp_path / "session.jsonl"
        log.write_text(
            json.dumps({"type": "human", "message": {"content": "hello"}}) + "\n"
        )
        assert extract_last_assistant_text(log) == ""

    def test_returns_empty_for_missing_file(self, tmp_path):
        assert extract_last_assistant_text(tmp_path / "nope.jsonl") == ""

    def test_picks_last_assistant_not_first(self, tmp_path):
        log = tmp_path / "session.jsonl"
        log.write_text(
            json.dumps({
                "type": "assistant",
                "message": {"content": "first message"}
            }) + "\n"
            + json.dumps({
                "type": "assistant",
                "message": {"content": "second message with defer"}
            }) + "\n"
        )
        text = extract_last_assistant_text(log)
        assert "second message" in text


# --- detect_deferral ---


class TestDetectDeferral:
    def test_detects_new_session_suggestion(self):
        assert detect_deferral("Let's start a new session for this complex task.")

    def test_detects_continue_later(self):
        assert detect_deferral("We should continue this later in a fresh session.")

    def test_detects_defer(self):
        assert detect_deferral("I'd suggest we defer this to the next session.")

    def test_detects_too_complex(self):
        assert detect_deferral("This is too complex to finish now, let's pick it up next time.")

    def test_detects_running_low_on_context(self):
        assert detect_deferral("We're running low on context, I recommend starting fresh.")

    def test_detects_pick_up_next_time(self):
        assert detect_deferral("Let's pick this up in a new conversation.")

    def test_detects_fresh_session(self):
        assert detect_deferral("A fresh session would be better for this task.")

    def test_detects_context_limit(self):
        assert detect_deferral("We're approaching the context limit, should wrap up.")

    def test_no_false_positive_on_normal_text(self):
        assert not detect_deferral("I'll implement this feature now. Let me start by reading the code.")

    def test_no_false_positive_on_session_word_alone(self):
        assert not detect_deferral("The session state is stored in .session/state.json")

    def test_no_false_positive_on_context_word_alone(self):
        assert not detect_deferral("Let me check the context of this function.")

    def test_returns_matched_pattern(self):
        result = detect_deferral("Let's start a new session.")
        assert result  # truthy — the matched pattern string


# --- run_deferral_check (integration) ---


class TestRunDeferralCheck:
    def test_returns_empty_when_no_deferral(self, tmp_path):
        log = tmp_path / "session.jsonl"
        log.write_text(
            json.dumps({
                "type": "assistant",
                "message": {"content": "I'll build this feature now."}
            }) + "\n"
        )
        with patch("deferral_detect.find_latest_session_log", return_value=log):
            _, output = run_deferral_check('{"prompt": "yes build it"}')
        assert output == ""

    def test_returns_counter_message_on_deferral(self, tmp_path):
        log = tmp_path / "session.jsonl"
        log.write_text(
            json.dumps({
                "type": "assistant",
                "message": {"content": "This is too complex, let's continue in a new session."}
            }) + "\n"
        )
        with patch("deferral_detect.find_latest_session_log", return_value=log), \
             patch("deferral_detect._get_session_stats", return_value={
                 "exchanges": 15, "bytes": 50000, "bytes_limit": 700000,
             }):
            _, output = run_deferral_check('{"prompt": "ok"}')
        assert output  # non-empty
        parsed = json.loads(output)
        ctx = parsed["hookSpecificOutput"]["additionalContext"]
        assert "DEFERRAL DETECTED" in ctx
        assert "15" in ctx  # exchanges shown

    def test_returns_empty_when_no_log(self):
        with patch("deferral_detect.find_latest_session_log", return_value=None):
            _, output = run_deferral_check('{"prompt": "hello"}')
        assert output == ""

    def test_returns_empty_on_bad_input(self):
        with patch("deferral_detect.find_latest_session_log", return_value=None):
            _, output = run_deferral_check("not json")
        assert output == ""
