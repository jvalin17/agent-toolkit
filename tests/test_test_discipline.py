"""Interview rounds and test discipline, borrowed as content from mattpocock/skills (grilling, tdd,
to-spec seams) and kept behind our own gates.

Covers: the tautological-test diff scan and its precommit wiring, optional `seams` in the
execution plan, and the skill text that must carry the new discipline so it cannot silently regress.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from compliance import check_diff_for_tautological_tests, validate_execution_plan  # noqa: E402
import finalize_precommit as fp  # noqa: E402
from route_to_skill import SKILL_CONTEXTS  # noqa: E402


def _diff(path: str, added: list[str]) -> str:
    body = "\n".join(f"+{line}" for line in added)
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -1,1 +1,{len(added) + 1} @@\n{body}\n"


class TestTautologicalTestScan:
    @pytest.mark.parametrize("line", [
        "    assert True",
        "    self.assertTrue(True)",
        "    assert total == total",
        "    assert user.name == user.name",
        "  expect(true).toBe(true);",
        "  expect(result).toEqual(result);",
        "  expect(order.total).toBe(order.total)",
        "  expect(true).toBeTruthy();",
    ])
    def test_flags_assertions_that_cannot_fail(self, line):
        found = check_diff_for_tautological_tests(_diff("tests/test_orders.py", [line]))
        assert len(found) == 1
        assert "tests/test_orders.py" in found[0]
        assert line.strip() in found[0]

    @pytest.mark.parametrize("line", [
        "    assert calculate_total([{'price': 10}, {'price': 5}]) == 15",
        "    assert user.name == 'Maria Garcia'",
        "  expect(results).toHaveLength(1);",
        "  expect(order.total).toBe(15);",
        "    assert truthy_flag is True",
        "    with pytest.raises(DuplicateEmailError):",
    ])
    def test_real_assertions_pass(self, line):
        assert check_diff_for_tautological_tests(_diff("tests/test_orders.py", [line])) == []

    def test_ignores_source_files_and_removed_lines(self):
        source = _diff("src/orders.py", ["    assert True  # guard"])
        assert check_diff_for_tautological_tests(source) == []
        removed = "diff --git a/tests/test_a.py b/tests/test_a.py\n--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1,1 +0,0 @@\n-    assert True\n"
        assert check_diff_for_tautological_tests(removed) == []

    def test_ignores_nested_diff_text_and_empty_diff(self):
        assert check_diff_for_tautological_tests("") == []
        nested = _diff("tests/test_a.py", ["+    assert True"])  # a diff quoted inside a test string
        assert check_diff_for_tautological_tests(nested) == []


class TestPrecommitWiring:
    def test_tautologies_block_the_commit(self):
        reasons = fp._diff_reasons(None, None, ["tests/test_a.py: assert True"])
        assert len(reasons) == 1
        assert "tautolog" in reasons[0].lower()
        assert "tests/test_a.py" in reasons[0]

    def test_no_reason_without_tautologies(self):
        assert fp._diff_reasons(None, None, []) == []
        assert fp._diff_reasons(None, None, None) == []

    def test_decide_precommit_accepts_the_new_finding(self, monkeypatch):
        from gate.attest import CheckResult

        green = CheckResult("tests", True)
        findings = {
            "skill": "precommit", "slug": "s",
            "instructions": {"addressed": 1, "total": 1, "items": []},
            "rules": {"violations": 0, "items": []},
            "readme": {"passed": True, "details": ""},
            "tests_meaningful": {"result": "verified", "evidence": ""},
            "app_verification": {"status": "na", "notes": ""},
        }
        ready, reasons = fp._decide_precommit(
            findings, green, green, tautological_tests=["tests/test_a.py: expect(true).toBe(true)"],
        )
        assert ready is False
        assert any("tautolog" in r.lower() for r in reasons)


class TestExecutionPlanSeams:
    def _plan(self, seams):
        slab = {"name": "checkout", "build_role": "backend", "review_roles": ["qa"], "skills": ["precommit"]}
        if seams is not None:
            slab["seams"] = seams
        return {"feature": "checkout", "slabs": [slab]}

    def test_seams_optional(self):
        assert validate_execution_plan(self._plan(None)) == []

    def test_seams_list_of_strings_accepted(self):
        assert validate_execution_plan(self._plan(["POST /checkout", "Cart.total()"])) == []

    @pytest.mark.parametrize("bad", ["POST /checkout", [1, 2], [""]])
    def test_malformed_seams_rejected(self, bad):
        errors = validate_execution_plan(self._plan(bad))
        assert any("seams" in e for e in errors)


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _non_empty_lines(rel: str) -> int:
    return sum(1 for line in _text(rel).splitlines() if line.strip())


class TestInterviewContent:
    STUB = "skills/requirements/SKILL.md"

    def test_rounds_over_the_frontier_with_recommendations(self):
        text = _text(self.STUB)
        for needle in ("frontier", "round", "➡️", "design tree", "recommended answer"):
            assert needle in text, needle

    def test_facts_are_the_agents_job_decisions_are_the_users(self):
        text = _text(self.STUB)
        assert "Facts" in text and "decisions" in text
        assert "functional-researcher" in text

    def test_ends_on_shared_understanding_not_a_question_count(self):
        text = _text(self.STUB)
        assert "shared understanding" in text
        assert "20 questions" not in text
        assert "ONE AT A TIME" not in text

    def test_ungrillable_questions_get_something_to_react_to(self):
        assert "ungrillable" in _text(self.STUB).lower()

    def test_stub_stays_short(self):
        assert _non_empty_lines(self.STUB) <= 150

    def test_guardrail_counts_rounds(self):
        full = _text("shared/guardrails.md")
        quick = _text("shared/guardrails-quick.md")
        assert "G-REQ-1" in full and "round" in full.split("G-REQ-1", 1)[1][:600].lower()
        assert "20 questions max" not in full and "20 questions max" not in quick

    def test_routing_hook_no_longer_prescribes_two_questions(self):
        for key in ("build", "requirements"):
            assert "Q1 + Q4" not in SKILL_CONTEXTS[key]
            assert "Q1 (what?)" not in SKILL_CONTEXTS[key]
        assert "round" in SKILL_CONTEXTS["requirements"].lower()


class TestTestDisciplineContent:
    def test_tdd_module_carries_seams_and_the_three_anti_patterns(self):
        text = _text("skills/implementation/modules/tdd.md")
        for needle in ("seam", "Implementation-coupled", "Tautological", "Horizontal slicing",
                       "Red before green", "vertical slice", "system boundaries"):
            assert needle in text, needle

    def test_execution_plan_schema_documents_seams(self):
        assert '"seams"' in _text("skills/implementation/modules/workflow.md")

    def test_precommit_reference_shows_tautological_and_coupled_tests(self):
        text = _text("skills/precommit/references/test-quality.md")
        assert "Tautological" in text and "Implementation-coupled" in text
        assert "seam" in text.lower()

    def test_precommit_workflow_checks_seams(self):
        assert "seam" in _text("skills/precommit/modules/workflow.md").lower()

    def test_reviewer_tests_module_checks_seams(self):
        text = _text("skills/reviewer/tests.md")
        assert "seam" in text.lower()
        assert "Tautolog" in text or "tautolog" in text
