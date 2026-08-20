#!/usr/bin/env python3
"""Tests for hooks/compliance.py — role rule compliance tracking."""

import json
import time
from pathlib import Path

import pytest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))


class TestComplianceTracker:
    def test_record_obeyed(self, tmp_path):
        from compliance import ComplianceTracker

        tracker = ComplianceTracker(tmp_path)
        tracker.record("backend", "paginate all list endpoints", "obeyed",
                       evidence="src/routes/stats.ts:42 — cursor pagination")

        data = tracker.load()
        assert len(data["records"]) == 1
        assert data["records"][0]["status"] == "obeyed"
        assert data["records"][0]["role"] == "backend"

    def test_record_violated(self, tmp_path):
        from compliance import ComplianceTracker

        tracker = ComplianceTracker(tmp_path)
        tracker.record("dba", "no SELECT *", "violated",
                       evidence="src/models/user.ts:15 — SELECT * FROM users")

        data = tracker.load()
        assert data["records"][0]["status"] == "violated"

    def test_multiple_records(self, tmp_path):
        from compliance import ComplianceTracker

        tracker = ComplianceTracker(tmp_path)
        tracker.record("backend", "rule1", "obeyed", evidence="file:1")
        tracker.record("backend", "rule2", "violated", evidence="file:2")
        tracker.record("security", "rule3", "obeyed", evidence="file:3")

        data = tracker.load()
        assert len(data["records"]) == 3

    def test_summary(self, tmp_path):
        from compliance import ComplianceTracker

        tracker = ComplianceTracker(tmp_path)
        tracker.record("backend", "r1", "obeyed", evidence="f:1")
        tracker.record("backend", "r2", "violated", evidence="f:2")
        tracker.record("backend", "r3", "obeyed", evidence="f:3")
        tracker.record("security", "r4", "obeyed", evidence="f:4")

        summary = tracker.summary()
        assert summary["total"] == 4
        assert summary["obeyed"] == 3
        assert summary["violated"] == 1
        assert summary["compliance_rate"] == 75.0
        assert summary["by_role"]["backend"]["obeyed"] == 2
        assert summary["by_role"]["backend"]["violated"] == 1
        assert summary["by_role"]["security"]["obeyed"] == 1

    def test_persists_to_file(self, tmp_path):
        from compliance import ComplianceTracker

        tracker1 = ComplianceTracker(tmp_path)
        tracker1.record("backend", "rule1", "obeyed", evidence="f:1")

        # Load from same path — should see the record
        tracker2 = ComplianceTracker(tmp_path)
        data = tracker2.load()
        assert len(data["records"]) == 1

    def test_empty_tracker(self, tmp_path):
        from compliance import ComplianceTracker

        tracker = ComplianceTracker(tmp_path)
        summary = tracker.summary()
        assert summary["total"] == 0
        assert summary["compliance_rate"] == 100.0

    def test_violated_rules_list(self, tmp_path):
        from compliance import ComplianceTracker

        tracker = ComplianceTracker(tmp_path)
        tracker.record("backend", "paginate endpoints", "obeyed", evidence="f:1")
        tracker.record("dba", "no SELECT *", "violated", evidence="src/user.ts:15")
        tracker.record("security", "no secrets in code", "violated", evidence=".env committed")

        violated = tracker.violated_rules()
        assert len(violated) == 2
        assert any("SELECT *" in v["rule"] for v in violated)
        assert any("secrets" in v["rule"] for v in violated)


class TestEvidenceVerification:
    def test_evidence_required_for_done_claim(self, tmp_path):
        from compliance import verify_evidence

        # Claim with evidence — passes
        result = verify_evidence(
            claim="all tests pass",
            evidence="$ python3 -m pytest tests/ -q\n24 passed in 0.5s",
        )
        assert result["verified"] is True

    def test_no_evidence_fails(self, tmp_path):
        from compliance import verify_evidence

        result = verify_evidence(
            claim="all tests pass",
            evidence="",
        )
        assert result["verified"] is False
        assert "no evidence" in result["reason"].lower()

    def test_vague_evidence_fails(self, tmp_path):
        from compliance import verify_evidence

        result = verify_evidence(
            claim="all tests pass",
            evidence="tests pass",
        )
        assert result["verified"] is False
        assert "vague" in result["reason"].lower() or "insufficient" in result["reason"].lower()

    def test_evidence_with_command_output(self, tmp_path):
        from compliance import verify_evidence

        result = verify_evidence(
            claim="API returns correct response",
            evidence="$ curl localhost:3000/api/health\n{\"status\": \"ok\"}",
        )
        assert result["verified"] is True

    def test_evidence_with_file_reference(self, tmp_path):
        from compliance import verify_evidence

        result = verify_evidence(
            claim="input validation added",
            evidence="src/routes/users.ts:42 — z.object({ email: z.string().email() })",
        )
        assert result["verified"] is True
