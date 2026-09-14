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

    def test_does_not_match_function_calls_as_definitions(self):
        """Regression: the Java/C# regex must not match indented function
        calls like select(Round) or process(data)."""
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/src/app.py b/src/app.py
--- a/src/app.py
+++ b/src/app.py
@@ -1,3 +1,8 @@
+    select(Round)
+    items.append(x)
+    result = process(data)
+    for item in collection(items):
+        self.validate(input)
 def existing():
     pass
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) == 0, f"False positives: {result}"

    def test_detects_java_method_definition(self):
        from compliance import check_diff_for_untested_functions

        diff = """diff --git a/src/App.java b/src/App.java
--- a/src/App.java
+++ b/src/App.java
@@ -1,3 +1,6 @@
+public void calculateTotal(List items) {
+    return items.stream().sum();
+}
 public class App {}
"""
        result = check_diff_for_untested_functions(diff)
        assert len(result) > 0
        assert any("calculateTotal" in r for r in result)

    def test_empty_diff(self):
        from compliance import check_diff_for_untested_functions

        result = check_diff_for_untested_functions("")
        assert len(result) == 0


class TestCheckDiffForNoqaInTests:
    """check_diff_for_noqa_in_tests scans a git diff for added # noqa
    comments in test files — a sign the agent is fighting the linter."""

    def test_detects_noqa_added_to_test_file(self):
        from compliance import check_diff_for_noqa_in_tests

        diff = """diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,3 +1,6 @@
+def testCalculateTotal():  # noqa: N802
+    assert True
+
 def test_existing():
     pass
"""
        result = check_diff_for_noqa_in_tests(diff)
        assert len(result) == 1
        assert "noqa" in result[0]
        assert "tests/test_foo.py" in result[0]

    def test_no_warning_for_noqa_in_source_file(self):
        from compliance import check_diff_for_noqa_in_tests

        diff = """diff --git a/src/foo.py b/src/foo.py
--- a/src/foo.py
+++ b/src/foo.py
@@ -1,3 +1,6 @@
+import something  # noqa: F401
+
 def existing():
     pass
"""
        result = check_diff_for_noqa_in_tests(diff)
        assert len(result) == 0

    def test_no_warning_for_clean_test(self):
        from compliance import check_diff_for_noqa_in_tests

        diff = """diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,3 +1,6 @@
+def test_calculate_total():
+    assert True
+
 def test_existing():
     pass
"""
        result = check_diff_for_noqa_in_tests(diff)
        assert len(result) == 0

    def test_detects_multiple_noqa_lines(self):
        from compliance import check_diff_for_noqa_in_tests

        diff = """diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,5 +1,8 @@
+def testFoo():  # noqa: N802
+    pass
+def testBar():  # noqa: N802
+    pass
+
 def test_existing():
     pass
"""
        result = check_diff_for_noqa_in_tests(diff)
        assert len(result) == 2

    def test_empty_diff(self):
        from compliance import check_diff_for_noqa_in_tests

        result = check_diff_for_noqa_in_tests("")
        assert len(result) == 0

    def test_ignores_existing_noqa_not_in_diff(self):
        from compliance import check_diff_for_noqa_in_tests

        # The context line (no + prefix) contains a noqa directive
        # but it's not an added line, so it should be ignored
        noqa_directive = "# noqa: N802"
        diff = (
            "diff --git a/tests/test_foo.py b/tests/test_foo.py\n"
            "--- a/tests/test_foo.py\n"
            "+++ b/tests/test_foo.py\n"
            "@@ -1,3 +1,6 @@\n"
            "+def test_new():\n"
            "+    pass\n"
            "+\n"
            f" def old_thing():  {noqa_directive}\n"
            "     pass\n"
        )
        result = check_diff_for_noqa_in_tests(diff)
        assert len(result) == 0

    def test_ignores_noqa_inside_string_literals(self):
        from compliance import check_diff_for_noqa_in_tests

        diff = """diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,3 +1,6 @@
+        warnings = ["file.py: added '# noqa' suppression"]
+        assert "noqa" in result[0]
+
 def test_existing():
     pass
"""
        result = check_diff_for_noqa_in_tests(diff)
        assert len(result) == 0

    def test_ignores_nested_diff_content(self):
        from compliance import check_diff_for_noqa_in_tests

        diff = """diff --git a/tests/test_foo.py b/tests/test_foo.py
--- a/tests/test_foo.py
+++ b/tests/test_foo.py
@@ -1,3 +1,6 @@
++def testFoo():  # noqa: N802
++    pass
+
 def test_existing():
     pass
"""
        result = check_diff_for_noqa_in_tests(diff)
        assert len(result) == 0


# --- Session summary -------------------------------------------------------


class TestGenerateSessionSummary:
    """generate_session_summary reads a JSONL log and produces a markdown summary."""

    def test_summary_includes_skills(self, tmp_path):
        from compliance import generate_session_summary

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Skill", {"skill": "implementation"}),
            _tool_use_entry("Skill", {"skill": "precommit"}),
        ])
        summary = generate_session_summary(log)
        assert "implementation" in summary
        assert "precommit" in summary

    def test_summary_includes_files_changed(self, tmp_path):
        from compliance import generate_session_summary

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Edit", {"file_path": "/project/src/foo.py", "old_string": "a", "new_string": "b"}),
            _tool_use_entry("Write", {"file_path": "/project/tests/test_foo.py", "content": "x"}),
        ])
        summary = generate_session_summary(log)
        assert "foo.py" in summary
        assert "test_foo.py" in summary

    def test_summary_includes_test_results(self, tmp_path):
        from compliance import generate_session_summary

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Bash", {"command": "python3 -m pytest tests/ -q"}),
            {
                "type": "tool_result",
                "message": {"content": "806 passed, 1 skipped in 12.5s"},
            },
        ])
        summary = generate_session_summary(log)
        assert "806 passed" in summary

    def test_summary_includes_roles(self, tmp_path):
        from compliance import generate_session_summary

        log = _make_jsonl(tmp_path, [
            _tool_use_entry("Agent", {
                "description": "QA role review",
                "prompt": "Review as QA role — check test coverage",
                "model": "sonnet",
            }),
        ])
        summary = generate_session_summary(log)
        assert "QA" in summary or "qa" in summary

    def test_empty_log(self, tmp_path):
        from compliance import generate_session_summary

        log = _make_jsonl(tmp_path, [])
        summary = generate_session_summary(log)
        assert "No toolkit activity" in summary

    def test_missing_log(self, tmp_path):
        from compliance import generate_session_summary

        summary = generate_session_summary(tmp_path / "nonexistent.jsonl")
        assert "unavailable" in summary.lower() or "not found" in summary.lower()


# --- Test redundancy detection ---------------------------------------------


class TestDetectTestRedundancy:
    """detect_test_redundancy scans test files for potentially redundant tests."""

    def test_detects_similar_test_names(self, tmp_path):
        from compliance import detect_test_redundancy

        test_file = tmp_path / "test_auth.py"
        test_file.write_text(
            "def test_login_success():\n    pass\n"
            "def test_login_succeeds():\n    pass\n"
            "def test_login_works():\n    pass\n"
            "def test_login_valid_creds():\n    pass\n"
        )
        findings = detect_test_redundancy([test_file])
        assert len(findings) > 0
        assert any("login" in f["group"] for f in findings)

    def test_no_redundancy_in_distinct_tests(self, tmp_path):
        from compliance import detect_test_redundancy

        test_file = tmp_path / "test_auth.py"
        test_file.write_text(
            "def test_login_success():\n    pass\n"
            "def test_logout():\n    pass\n"
            "def test_register():\n    pass\n"
        )
        findings = detect_test_redundancy([test_file])
        assert len(findings) == 0

    def test_detects_across_files(self, tmp_path):
        from compliance import detect_test_redundancy

        f1 = tmp_path / "test_auth.py"
        f1.write_text(
            "def test_login_success():\n    pass\n"
            "def test_login_valid():\n    pass\n"
            "def test_login_happy_path():\n    pass\n"
        )
        f2 = tmp_path / "test_auth2.py"
        f2.write_text(
            "def test_login_works():\n    pass\n"
        )
        findings = detect_test_redundancy([f1, f2])
        assert len(findings) > 0

    def test_empty_file_list(self):
        from compliance import detect_test_redundancy

        findings = detect_test_redundancy([])
        assert findings == []

    def test_returns_file_locations(self, tmp_path):
        from compliance import detect_test_redundancy

        test_file = tmp_path / "test_calc.py"
        test_file.write_text(
            "def test_add_numbers():\n    pass\n"
            "def test_add_integers():\n    pass\n"
            "def test_add_values():\n    pass\n"
        )
        findings = detect_test_redundancy([test_file])
        assert len(findings) > 0
        assert "tests" in findings[0] or "test_names" in findings[0]
        assert len(findings[0].get("test_names", [])) >= 3


# --- Test plan validation -------------------------------------------------


class TestValidateTestPlan:
    """validate_test_plan checks that a test plan JSON is well-formed."""

    def test_valid_plan(self):
        from compliance import validate_test_plan

        plan = {
            "feature": "user-auth",
            "cases": [
                {"id": "TC1", "description": "Login succeeds with valid creds",
                 "test_file": "tests/test_auth.py", "test_name": "test_login_success"},
            ],
            "edge_cases": ["empty password"],
            "created_at": "2026-09-13T10:00:00",
        }
        errors = validate_test_plan(plan)
        assert errors == []

    def test_missing_feature(self):
        from compliance import validate_test_plan

        plan = {"cases": [], "edge_cases": [], "created_at": "2026-09-13"}
        errors = validate_test_plan(plan)
        assert any("feature" in e for e in errors)

    def test_empty_cases(self):
        from compliance import validate_test_plan

        plan = {"feature": "x", "cases": [], "edge_cases": [], "created_at": "2026-09-13"}
        errors = validate_test_plan(plan)
        assert any("cases" in e.lower() for e in errors)

    def test_case_missing_fields(self):
        from compliance import validate_test_plan

        plan = {
            "feature": "x",
            "cases": [{"id": "TC1"}],
            "edge_cases": [],
            "created_at": "2026-09-13",
        }
        errors = validate_test_plan(plan)
        assert any("description" in e or "test_file" in e or "test_name" in e for e in errors)


class TestCheckTestPlanCoverage:
    """check_test_plan_coverage verifies each planned test case exists."""

    def test_all_cases_covered(self, tmp_path):
        from compliance import check_test_plan_coverage

        test_file = tmp_path / "tests" / "test_auth.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("def test_login_success():\n    assert True\n")

        plan = {
            "feature": "user-auth",
            "cases": [
                {"id": "TC1", "description": "Login succeeds",
                 "test_file": "tests/test_auth.py", "test_name": "test_login_success"},
            ],
            "edge_cases": [],
            "created_at": "2026-09-13",
        }
        missing = check_test_plan_coverage(plan, tmp_path)
        assert missing == []

    def test_missing_test_function(self, tmp_path):
        from compliance import check_test_plan_coverage

        test_file = tmp_path / "tests" / "test_auth.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("def test_other():\n    assert True\n")

        plan = {
            "feature": "user-auth",
            "cases": [
                {"id": "TC1", "description": "Login succeeds",
                 "test_file": "tests/test_auth.py", "test_name": "test_login_success"},
            ],
            "edge_cases": [],
            "created_at": "2026-09-13",
        }
        missing = check_test_plan_coverage(plan, tmp_path)
        assert len(missing) == 1
        assert "TC1" in missing[0]

    def test_missing_test_file(self, tmp_path):
        from compliance import check_test_plan_coverage

        plan = {
            "feature": "user-auth",
            "cases": [
                {"id": "TC1", "description": "Login succeeds",
                 "test_file": "tests/test_auth.py", "test_name": "test_login_success"},
            ],
            "edge_cases": [],
            "created_at": "2026-09-13",
        }
        missing = check_test_plan_coverage(plan, tmp_path)
        assert len(missing) == 1

    def test_multiple_cases_partial_coverage(self, tmp_path):
        from compliance import check_test_plan_coverage

        test_file = tmp_path / "tests" / "test_auth.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("def test_login_success():\n    assert True\n")

        plan = {
            "feature": "user-auth",
            "cases": [
                {"id": "TC1", "description": "Login succeeds",
                 "test_file": "tests/test_auth.py", "test_name": "test_login_success"},
                {"id": "TC2", "description": "Login fails with bad password",
                 "test_file": "tests/test_auth.py", "test_name": "test_login_bad_password"},
            ],
            "edge_cases": [],
            "created_at": "2026-09-13",
        }
        missing = check_test_plan_coverage(plan, tmp_path)
        assert len(missing) == 1
        assert "TC2" in missing[0]


class TestFormatTestPlanSummary:
    """format_test_plan_summary produces a markdown summary for project-state."""

    def test_produces_markdown(self):
        from compliance import format_test_plan_summary

        plan = {
            "feature": "user-auth",
            "cases": [
                {"id": "TC1", "description": "Login succeeds",
                 "test_file": "tests/test_auth.py", "test_name": "test_login_success"},
                {"id": "TC2", "description": "Login fails",
                 "test_file": "tests/test_auth.py", "test_name": "test_login_failure"},
            ],
            "edge_cases": ["empty password", "SQL injection"],
            "created_at": "2026-09-13",
        }
        summary = format_test_plan_summary(plan)
        assert "user-auth" in summary
        assert "TC1" in summary
        assert "TC2" in summary
        assert "test_login_success" in summary
        assert "empty password" in summary
        assert "SQL injection" in summary
