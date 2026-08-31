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


# --- Session action auditing (mechanical verification) --------------------


def _make_jsonl(tmp_path: Path, entries: list[dict]) -> Path:
    """Write a fake session JSONL for audit_session_actions to read."""
    log = tmp_path / "session.jsonl"
    lines = [json.dumps(e) for e in entries]
    log.write_text("\n".join(lines))
    return log


def _tool_use_entry(name: str, input_data: dict) -> dict:
    """Create a JSONL entry simulating a tool_use call."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "name": name, "input": input_data}
            ]
        },
    }


class TestAuditSessionActions:
    """audit_session_actions reads the session JSONL and mechanically verifies
    what actually happened — server starts, HTTP requests, role agents, TDD ordering."""

    def test_detects_server_start(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Bash", {"command": "npm start &"}),
            _tool_use_entry("Bash", {"command": "curl http://localhost:3000/health"}),
        ])
        result = audit_session_actions(log)
        assert result["server_started"] is True
        assert result["http_request_made"] is True

    def test_detects_no_server_activity(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Bash", {"command": "git status"}),
            _tool_use_entry("Read", {"file_path": "/some/file.py"}),
        ])
        result = audit_session_actions(log)
        assert result["server_started"] is False
        assert result["http_request_made"] is False

    def test_detects_python_server_start(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Bash", {"command": "python3 -m flask run --port 5000"}),
            _tool_use_entry("Bash", {"command": "curl localhost:5000/api/test"}),
        ])
        result = audit_session_actions(log)
        assert result["server_started"] is True

    def test_detects_webfetch_as_http_request(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Bash", {"command": "npm run dev &"}),
            _tool_use_entry("WebFetch", {"url": "http://localhost:3000"}),
        ])
        result = audit_session_actions(log)
        assert result["http_request_made"] is True

    def test_detects_role_agents(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Agent", {
                "description": "QA role review",
                "prompt": "Review as QA role — check test coverage",
                "model": "sonnet",
            }),
            _tool_use_entry("Agent", {
                "description": "Security role review",
                "prompt": "Review as Security role — check auth",
                "model": "sonnet",
            }),
        ])
        result = audit_session_actions(log)
        assert result["role_agents_spawned"] >= 2

    def test_detects_no_role_agents(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Agent", {
                "description": "Search for files",
                "prompt": "Find all test files",
                "model": "haiku",
            }),
        ])
        result = audit_session_actions(log)
        assert result["role_agents_spawned"] == 0

    def test_detects_tdd_order_correct(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Edit", {"file_path": "/project/tests/test_foo.py", "old_string": "a", "new_string": "b"}),
            _tool_use_entry("Edit", {"file_path": "/project/src/foo.py", "old_string": "c", "new_string": "d"}),
        ])
        result = audit_session_actions(log)
        assert result["tdd_order_respected"] is True

    def test_detects_tdd_order_violated(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Edit", {"file_path": "/project/src/foo.py", "old_string": "a", "new_string": "b"}),
            _tool_use_entry("Edit", {"file_path": "/project/tests/test_foo.py", "old_string": "c", "new_string": "d"}),
        ])
        result = audit_session_actions(log)
        assert result["tdd_order_respected"] is False

    def test_empty_log(self, tmp_path):
        from compliance import audit_session_actions

        log = _make_jsonl(tmp_path, [])
        result = audit_session_actions(log)
        assert result["server_started"] is False
        assert result["http_request_made"] is False
        assert result["role_agents_spawned"] == 0
        assert result["tdd_order_respected"] is True  # vacuously true

    def test_missing_log_file(self, tmp_path):
        from compliance import audit_session_actions

        result = audit_session_actions(tmp_path / "nonexistent.jsonl")
        assert result["available"] is False


class TestCheckDiffForUntested:
    """check_diff_for_untested_functions scans a git diff and finds new
    functions/methods in source files that have no corresponding new test."""

    def test_detects_new_function_without_test(self):
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/src/foo.py b/src/foo.py
--- a/src/foo.py
+++ b/src/foo.py
@@ -1,3 +1,6 @@
+def calculate_total(items):
+    return sum(i.price for i in items)
+
 def existing():
     pass
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) > 0
        assert any("calculate_total" in r for r in result)

    def test_no_warning_when_test_added(self):
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/src/foo.py b/src/foo.py
--- a/src/foo.py
+++ b/src/foo.py
@@ -1,3 +1,6 @@
+def calculate_total(items):
+    return sum(i.price for i in items)
+
 def existing():
     pass
diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,3 +1,6 @@
+def test_calculate_total():
+    assert calculate_total([]) == 0
+
 def test_existing():
     pass
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) == 0

    def test_ignores_test_files(self):
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,3 +1,6 @@
+def test_new_feature():
+    assert True
+
 def test_existing():
     pass
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) == 0

    def test_ignores_hook_and_config_files(self):
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/hooks/my_hook.py b/hooks/my_hook.py
--- a/hooks/my_hook.py
+++ b/hooks/my_hook.py
@@ -1,3 +1,6 @@
+def new_hook_function():
+    pass
+
 def main():
     pass
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) == 0

    def test_detects_js_function(self):
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/src/utils.js b/src/utils.js
--- a/src/utils.js
+++ b/src/utils.js
@@ -1,3 +1,6 @@
+function formatPrice(amount) {
+  return `$${amount.toFixed(2)}`;
+}
+
 function existing() {}
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) > 0
        assert any("formatPrice" in r for r in result)

    def test_detects_class_method(self):
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/src/user.py b/src/user.py
--- a/src/user.py
+++ b/src/user.py
@@ -1,3 +1,6 @@
 class User:
+    def validate_email(self):
+        return "@" in self.email
+
     def __init__(self):
         pass
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) > 0
        assert any("validate_email" in r for r in result)

    def test_ignores_private_dunder_methods(self):
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/src/user.py b/src/user.py
--- a/src/user.py
+++ b/src/user.py
@@ -1,3 +1,6 @@
 class User:
+    def __repr__(self):
+        return f"User({self.name})"
+
     pass
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) == 0

    def test_empty_diff(self):
        from compliance import check_diff_for_untested_functions

        result = check_diff_for_untested_functions("")
        assert len(result) == 0
