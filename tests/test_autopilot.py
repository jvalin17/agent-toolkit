"""/autopilot — one entry point that runs every required toolkit skill and keeps the agent in the loop.

Covers the state module, the hook wiring (resume context, enforce message, push-needs-precommit on
both the Claude hook and the CLI gate) and the skill stub + catalog entries. Host-neutral by design.
"""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))
sys.path.insert(0, str(ROOT / "scripts"))

import autopilot_state  # noqa: E402
from autopilot_state import (  # noqa: E402
    STATE_RELATIVE, current_step, is_active, push_requires, read_state, resume_context, state_path,
)
from gate_hook import _required_skills_for_action, load_gate_config  # noqa: E402
from route_to_skill import run_route_to_skill  # noqa: E402
from skill_enforce import NO_SKILL_MESSAGE  # noqa: E402

TOOLKIT_SKILLS = (
    "requirements", "architecture", "explore", "implementation", "debug_tool",
    "verify", "reviewer", "evaluate", "assess", "precommit",
)


def _write_state(project: Path, status: str = "running", steps=None) -> Path:
    path = state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "task": "add CSV export to the invoices page",
        "kind": "build",
        "auto": False,
        "status": status,
        "steps": steps or [
            {"name": "requirements", "status": "skipped", "reason": "requirements/invoices.md covers it"},
            {"name": "implementation", "status": "done"},
            {"name": "verify", "status": "pending"},
            {"name": "precommit", "status": "pending"},
            {"name": "commit", "status": "pending"},
        ],
        "updated_at": "2026-10-15T10:00:00Z",
    }
    path.write_text(json.dumps(state), encoding="utf-8")
    return path


def _gates(project: Path, mode: str = "default") -> None:
    (project / "gates.json").write_text(json.dumps({"gate_mode": "legacy", "mode": mode}), encoding="utf-8")


class TestStateModule:
    def test_state_path_is_under_scratch(self, tmp_path):
        assert state_path(tmp_path) == tmp_path / STATE_RELATIVE
        assert STATE_RELATIVE.parts[0] == ".scratch"  # agent-writable, never a protected path

    def test_missing_file_is_not_active(self, tmp_path):
        assert read_state(tmp_path) is None
        assert is_active(tmp_path) is False

    def test_running_state_is_active_and_resumes_at_first_open_step(self, tmp_path):
        _write_state(tmp_path)
        state = read_state(tmp_path)
        assert is_active(tmp_path) is True
        assert current_step(state) == (3, 5, "verify")

    def test_paused_is_active_complete_is_not(self, tmp_path):
        _write_state(tmp_path, status="paused")
        assert is_active(tmp_path) is True
        _write_state(tmp_path, status="complete")
        assert is_active(tmp_path) is False

    @pytest.mark.parametrize("junk", ["", "{not json", "[]", '{"status": "running"}'])
    def test_malformed_or_stepless_state_is_ignored(self, tmp_path, junk):
        path = state_path(tmp_path)
        path.parent.mkdir(parents=True)
        path.write_text(junk, encoding="utf-8")
        assert is_active(tmp_path) is False

    def test_resume_context_names_task_step_and_rules(self, tmp_path):
        _write_state(tmp_path)
        text = resume_context(read_state(tmp_path))
        assert text.startswith("AUTOPILOT ACTIVE")
        assert "add CSV export to the invoices page" in text
        assert "step 3/5: verify" in text
        assert "/autopilot" in text
        assert str(STATE_RELATIVE) in text

    def test_push_requires_adds_precommit_only_while_active(self, tmp_path):
        assert push_requires(["evaluate"], tmp_path) == ["evaluate"]
        _write_state(tmp_path)
        assert push_requires(["evaluate"], tmp_path) == ["evaluate", "precommit"]
        assert push_requires(["precommit", "reviewer"], tmp_path) == ["precommit", "reviewer"]  # no duplicate


class TestRoutingHook:
    def _ctx(self, output: str) -> str:
        return json.loads(output)["hookSpecificOutput"]["additionalContext"]

    def test_plain_prompt_while_active_gets_resume_context(self, tmp_path):
        _write_state(tmp_path)
        code, output = run_route_to_skill(json.dumps({"prompt": "ok go on"}), tmp_path)
        assert code == 0
        assert self._ctx(output).startswith("AUTOPILOT ACTIVE")

    def test_build_prompt_while_active_resumes_before_routing(self, tmp_path):
        _write_state(tmp_path)
        _, output = run_route_to_skill(json.dumps({"prompt": "build the export button"}), tmp_path)
        ctx = self._ctx(output)
        assert ctx.index("AUTOPILOT ACTIVE") < ctx.index("SKILL ROUTING")

    def test_slash_prompt_while_active_is_left_alone(self, tmp_path):
        _write_state(tmp_path)
        code, output = run_route_to_skill(json.dumps({"prompt": "/precommit invoices"}), tmp_path)
        assert (code, output) == (0, "")

    def test_no_resume_context_when_inactive(self, tmp_path):
        code, output = run_route_to_skill(json.dumps({"prompt": "ok go on"}), tmp_path)
        assert (code, output) == (0, "")

    @pytest.mark.parametrize("prompt", [
        "build a settings page", "fix the crash on login", "refactor the payment module", "quick fix the typo",
    ])
    def test_code_change_intents_point_at_autopilot(self, tmp_path, prompt):
        _, output = run_route_to_skill(json.dumps({"prompt": prompt}), tmp_path)
        assert "/autopilot" in self._ctx(output)

    def test_explore_intent_does_not_push_autopilot(self, tmp_path):
        _, output = run_route_to_skill(json.dumps({"prompt": "walk me through this repo"}), tmp_path)
        assert "/autopilot" not in self._ctx(output)


class TestEnforceMessage:
    def test_no_skill_block_names_autopilot_first(self):
        first_bullet = next(line for line in NO_SKILL_MESSAGE.splitlines() if line.startswith("- "))
        assert "/autopilot" in first_bullet


class TestPushNeedsPrecommit:
    def test_claude_gate_hook_default_mode(self, tmp_path):
        _gates(tmp_path, "default")
        config = load_gate_config(tmp_path)
        assert _required_skills_for_action(config, "push", tmp_path) == []
        _write_state(tmp_path)
        assert _required_skills_for_action(config, "push", tmp_path) == ["precommit"]
        assert _required_skills_for_action(config, "commit", tmp_path) == ["precommit"]

    def test_claude_gate_hook_safe_mode_keeps_mode_skills(self, tmp_path):
        _gates(tmp_path, "safe")
        _write_state(tmp_path)
        config = load_gate_config(tmp_path)
        assert _required_skills_for_action(config, "push", tmp_path) == ["reviewer", "precommit"]

    def test_gemini_cli_gate_matches(self, tmp_path):
        from atk import _required_for

        _gates(tmp_path, "default")
        assert _required_for(tmp_path, "push") == []
        _write_state(tmp_path)
        assert _required_for(tmp_path, "push") == ["precommit"]

    def test_complete_state_lifts_the_extra_requirement(self, tmp_path):
        _gates(tmp_path, "default")
        _write_state(tmp_path, status="complete")
        assert _required_skills_for_action(load_gate_config(tmp_path), "push", tmp_path) == []


class TestSkillStub:
    STUB = ROOT / "skills" / "autopilot" / "SKILL.md"

    def _lines(self):
        return [line for line in self.STUB.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_stub_exists_and_stays_short(self):
        assert self.STUB.is_file()
        assert len(self._lines()) <= 120

    def test_frontmatter_is_user_invocable(self):
        head = "\n".join(self._lines()[:6])
        assert "name: autopilot" in head
        assert "user-invocable: true" in head
        assert "disable-model-invocation: false" in head

    def test_stub_names_every_toolkit_skill_and_no_others(self):
        text = self.STUB.read_text(encoding="utf-8")
        for skill in TOOLKIT_SKILLS:
            assert skill in text, skill
        assert "Toolkit skills only" in text

    def test_stub_covers_every_host(self):
        text = self.STUB.read_text(encoding="utf-8")
        for needle in ("Claude Code", "Cursor", "Windsurf", "Codex", "Grok", "Gemini",
                       "get_skill", "stamp_skill", "toolkit_pull.py", "atk.py"):
            assert needle in text, needle

    def test_stub_states_the_three_promises(self):
        text = self.STUB.read_text(encoding="utf-8")
        assert str(STATE_RELATIVE) in text                      # stays in the loop across sessions
        assert "fresh `/precommit`" in text and "push" in text   # push always behind precommit
        assert "execution-plan.json" in text and "findings.json" in text  # the two re-work traps


class TestCatalog:
    @pytest.mark.parametrize("doc, needle", [
        ("README.md", "`/autopilot`"),
        ("README.md", "Skills (15)"),
        ("docs/skills.md", "`/autopilot`"),
        ("docs/workflow.md", "/autopilot"),
        ("rules/skills-index.md", "| autopilot |"),
    ])
    def test_listed(self, doc, needle):
        assert needle in (ROOT / doc).read_text(encoding="utf-8"), f"{doc} lacks {needle}"

    def test_readme_counts_agree(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "**15 skills**" in readme
        assert "(19 / 15 / 9)" in readme
        assert "14 skills" not in readme and "Skills (14)" not in readme
