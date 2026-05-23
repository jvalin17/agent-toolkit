"""Integration tests for strict mode — end-to-end drift detection.

Simulates a strict mode session: session init with mode=strict,
tool use events that accumulate drift, integrity checks that fire,
and threshold actions that trigger warnings or session restart.

These tests exercise the full flow through session_init + session_monitor
without mocking internal functions — only filesystem and env are controlled.
"""

import json
import os
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from hooks.session_init import load_session_config, init_session_state, build_context
from hooks.session_monitor import (
    DRIFT_CHECK_INTERVAL,
    SessionState,
    compute_drift_score,
    handle_post_tool_use,
    handle_user_prompt,
    is_real_system_query,
    detect_patch_forward,
    load_state,
    save_state,
)


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestStrictModeSessionLifecycle:
    """Simulate a strict mode session from init through drift detection."""

    def test_session_init_creates_strict_state(self, project_dir):
        """session_init stores mode=strict in state.json when gates.json says strict."""
        gates = {"gate_mode": "legacy", "mode": "strict"}
        (project_dir / "gates.json").write_text(json.dumps(gates))

        config = load_session_config(project_dir)
        assert config["mode"] == "strict"

        session_dir = project_dir / ".session"
        init_session_state(session_dir, mode=config["mode"])

        state_file = session_dir / "state.json"
        data = json.loads(state_file.read_text())
        assert data["mode"] == "strict"
        assert data["exchanges_since_query"] == 0
        assert data["patch_forward_count"] == 0

    def test_session_monitor_loads_strict_state(self, project_dir):
        """session_monitor reads mode from state.json and activates drift tracking."""
        session_dir = project_dir / ".session"
        init_session_state(session_dir, mode="strict")

        state_file = session_dir / "state.json"
        state = load_state(state_file)
        assert state.mode == "strict"

        # Simulate user prompts — counter should increment
        state, _ = handle_user_prompt(state)
        assert state.exchanges_since_query == 1
        state, _ = handle_user_prompt(state)
        assert state.exchanges_since_query == 2

    def test_drift_accumulates_without_queries(self, project_dir):
        """A session that never queries the real system accumulates drift."""
        state = SessionState(session_start=1000, mode="strict")

        # Simulate 10 exchanges with only Read/Edit — no real-system queries
        for _ in range(10):
            state, _ = handle_user_prompt(state)
            state = handle_post_tool_use(
                state, "file contents here",
                tool_name="Read", command=""
            )

        assert state.exchanges_since_query == 10
        score = compute_drift_score(
            state.exchanges_since_query,
            state.patch_forward_count,
            state.slabs_without_data,
        )
        # 10/10 * 0.4 = 0.4 (warning territory)
        assert abs(score - 0.4) < 0.001

    def test_query_resets_drift(self, project_dir):
        """A real-system query resets exchanges_since_query to 0."""
        state = SessionState(
            session_start=1000, mode="strict", exchanges_since_query=8
        )

        # curl resets the counter
        state = handle_post_tool_use(
            state, '{"users": [{"id": 1}]}',
            tool_name="Bash", command="curl https://api.example.com/users"
        )
        assert state.exchanges_since_query == 0

    def test_patch_forward_detected_in_session(self, project_dir):
        """Full sequence: test fails, source edited without investigation."""
        state = SessionState(session_start=1000, mode="strict")

        # Step 1: Run tests — they fail
        state = handle_post_tool_use(
            state, "FAILED tests/test_auth.py::test_login - AssertionError",
            tool_name="Bash", command="python3 -m pytest tests/test_auth.py"
        )
        assert state.last_tool_sequence[-1]["was_test"] is True
        assert state.last_tool_sequence[-1]["failed"] is True

        # Step 2: Edit source directly (no Read, no query between)
        state = handle_post_tool_use(
            state, "",
            tool_name="Edit", command="", file_path="src/auth.py"
        )

        # Should have detected patch-forward
        assert state.patch_forward_count == 1

    def test_investigation_prevents_patch_forward(self, project_dir):
        """Reading a file between test failure and edit prevents detection."""
        state = SessionState(session_start=1000, mode="strict")

        # Test fails
        state = handle_post_tool_use(
            state, "FAILED - AssertionError: expected 200 got 401",
            tool_name="Bash", command="python3 -m pytest tests/"
        )

        # Investigate by reading source
        state = handle_post_tool_use(
            state, "def login(user, password): ...",
            tool_name="Read", command=""
        )

        # Now edit — this is NOT patch-forward
        state = handle_post_tool_use(
            state, "",
            tool_name="Edit", command="", file_path="src/auth.py"
        )

        assert state.patch_forward_count == 0

    def test_integrity_check_fires_and_warns(self, project_dir):
        """At exchange 15 with moderate drift, integrity check injects warning."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=DRIFT_CHECK_INTERVAL - 1,
            exchanges_since_query=9,  # will become 10 after increment
        )

        state, response = handle_user_prompt(state)

        assert response is not None
        assert "INTEGRITY CHECK" in response
        assert "Drift score" in response
        # exchanges_since_query=10 → 1.0*0.4=0.4 → moderate drift
        assert "MODERATE DRIFT" in response or "HIGH DRIFT" in response

    def test_critical_drift_stops_session(self, project_dir):
        """At exchange 15 with max drift, session is stopped."""
        state = SessionState(
            session_start=1000,
            mode="strict",
            exchanges=DRIFT_CHECK_INTERVAL - 1,
            exchanges_since_query=10,  # becomes 11, capped at 1.0
            patch_forward_count=3,
            slabs_without_data=2,
        )

        state, response = handle_user_prompt(state)

        assert state.stopped == 2
        assert "CRITICAL DRIFT" in response

    def test_normal_mode_no_drift_tracking(self, project_dir):
        """Same scenario in normal mode — zero drift tracking."""
        state = SessionState(session_start=1000, mode="normal")

        for _ in range(20):
            state, _ = handle_user_prompt(state)
            state = handle_post_tool_use(
                state, "FAILED",
                tool_name="Bash", command="python3 -m pytest"
            )
            state = handle_post_tool_use(
                state, "",
                tool_name="Edit", command="", file_path="src/main.py"
            )

        assert state.exchanges_since_query == 0
        assert state.patch_forward_count == 0
        assert state.last_tool_sequence == []


class TestStrictModeContextInjection:
    """Verify session_init injects the right context for strict mode."""

    def test_strict_context_includes_all_markers(self):
        """Strict mode context has all required markers."""
        context = build_context(
            files=["- HANDOFF.md (PRIORITY — read this first)"],
            report_count=0,
            warnings=[],
            continuation=None,
            mode="strict",
        )
        assert "STRICT MODE ACTIVE" in context
        assert "G-IMPL-7" in context
        assert "/evaluate required before commit" in context
        # Should still have normal content
        assert "MANDATORY RULES" in context
        assert "G-SESSION-1" in context

    def test_env_var_activates_strict(self, project_dir):
        """AGENT_TOOLKIT_MODE=strict works even without gates.json."""
        with patch.dict(os.environ, {"AGENT_TOOLKIT_MODE": "strict"}):
            config = load_session_config(project_dir)
        assert config["mode"] == "strict"


class TestDriftScoreEdgeCases:
    """Verify drift score formula at boundary values."""

    def test_just_below_warning(self):
        """Score just under 0.3 should not trigger warning."""
        # exchanges=7 → 0.7*0.4=0.28
        score = compute_drift_score(7, 0, 0)
        assert score < 0.3

    def test_just_at_warning(self):
        """Score at 0.3+ triggers warning."""
        # exchanges=8 → 0.8*0.4=0.32
        score = compute_drift_score(8, 0, 0)
        assert score >= 0.3

    def test_combined_moderate_drift(self):
        """Multiple counters combine to push score into warning range."""
        # exchanges=5 → 0.5*0.4=0.2, patches=1 → 0.33*0.4=0.133, slabs=0 → 0
        score = compute_drift_score(5, 1, 0)
        assert 0.3 <= score <= 0.4

    def test_just_below_critical(self):
        """Score in 0.6-0.8 range — high but not restart."""
        # exchanges=10 → 0.4, patches=2 → 0.267, slabs=1 → 0.1 = 0.767
        score = compute_drift_score(10, 2, 1)
        assert 0.6 < score < 0.8

    def test_just_above_critical(self):
        """Score above 0.8 triggers restart."""
        # exchanges=10 → 0.4, patches=3 → 0.4, slabs=1 → 0.1 = 0.9
        score = compute_drift_score(10, 3, 1)
        assert score > 0.8
