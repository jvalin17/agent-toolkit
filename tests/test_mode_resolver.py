"""Tests for hooks/mode_resolver.py — consolidated mode system."""

import os
import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("AGENT_TOOLKIT_MODE", raising=False)


def _make_config(tmp_path, mode="default"):
    import json
    gates = tmp_path / "gates.json"
    gates.write_text(json.dumps({"mode": mode}))
    return tmp_path


class TestResolveMode:
    def test_minimal_mode(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("minimal")
        assert m.tdd is False
        assert m.plan is False
        assert m.precommit is False
        assert m.reviewer is False

    def test_tdd_mode(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("tdd")
        assert m.tdd is True
        assert m.plan is False
        assert m.precommit is False
        assert m.reviewer is False

    def test_planned_mode(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("planned")
        assert m.tdd is False
        assert m.plan is True
        assert m.precommit is False
        assert m.reviewer is False

    def test_guarded_mode(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("guarded")
        assert m.tdd is False
        assert m.plan is False
        assert m.precommit is True
        assert m.reviewer is False

    def test_default_mode(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("default")
        assert m.tdd is True
        assert m.plan is False
        assert m.precommit is True
        assert m.reviewer is False

    def test_standard_mode(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("standard")
        assert m.tdd is True
        assert m.plan is True
        assert m.precommit is True
        assert m.reviewer is False

    def test_safe_mode(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("safe")
        assert m.tdd is True
        assert m.plan is True
        assert m.precommit is True
        assert m.reviewer is True

    def test_unknown_mode_falls_back(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("nonexistent")
        # Falls back to default
        assert m.tdd is True
        assert m.precommit is True
        assert m.plan is False
        assert m.reviewer is False

    def test_env_var_override(self, monkeypatch):
        from mode_resolver import resolve_mode_from_config
        monkeypatch.setenv("AGENT_TOOLKIT_MODE", "safe")
        m = resolve_mode_from_config({"mode": "minimal"})
        assert m.tdd is True
        assert m.plan is True
        assert m.precommit is True
        assert m.reviewer is True


class TestRequiredSkills:
    def test_required_skills_for_commit(self):
        from mode_resolver import resolve_mode
        assert resolve_mode("minimal").commit_requires == []
        assert resolve_mode("guarded").commit_requires == ["precommit"]
        assert resolve_mode("default").commit_requires == ["precommit"]
        assert resolve_mode("standard").commit_requires == ["precommit"]
        assert resolve_mode("safe").commit_requires == ["precommit"]

    def test_required_skills_for_push_safe(self):
        from mode_resolver import resolve_mode
        m = resolve_mode("safe")
        assert "reviewer" in m.push_requires

    def test_is_tdd_enforced(self):
        from mode_resolver import resolve_mode
        assert resolve_mode("minimal").tdd is False
        assert resolve_mode("planned").tdd is False
        assert resolve_mode("guarded").tdd is False
        assert resolve_mode("tdd").tdd is True
        assert resolve_mode("default").tdd is True
        assert resolve_mode("standard").tdd is True
        assert resolve_mode("safe").tdd is True

    def test_is_plan_enforced(self):
        from mode_resolver import resolve_mode
        assert resolve_mode("minimal").plan is False
        assert resolve_mode("tdd").plan is False
        assert resolve_mode("guarded").plan is False
        assert resolve_mode("planned").plan is True
        assert resolve_mode("standard").plan is True
        assert resolve_mode("safe").plan is True


class TestSetMode:
    def test_set_mode_updates_gates_json(self, tmp_path):
        import json
        from mode_resolver import set_mode
        (tmp_path / "gates.json").write_text(json.dumps({"mode": "minimal"}))
        result = set_mode("safe", tmp_path)
        assert result.name == "safe"
        config = json.loads((tmp_path / "gates.json").read_text())
        assert config["mode"] == "safe"

    def test_set_mode_rejects_invalid(self, tmp_path):
        import json
        from mode_resolver import set_mode
        (tmp_path / "gates.json").write_text(json.dumps({"mode": "default"}))
        result = set_mode("nonexistent", tmp_path)
        assert result is None
        config = json.loads((tmp_path / "gates.json").read_text())
        assert config["mode"] == "default"

    def test_set_mode_preserves_other_fields(self, tmp_path):
        import json
        from mode_resolver import set_mode
        (tmp_path / "gates.json").write_text(json.dumps({
            "mode": "minimal", "model": "opus", "auto": True, "gate_mode": "legacy"
        }))
        set_mode("safe", tmp_path)
        config = json.loads((tmp_path / "gates.json").read_text())
        assert config["mode"] == "safe"
        assert config["model"] == "opus"
        assert config["auto"] is True
        assert config["gate_mode"] == "legacy"

    def test_set_mode_creates_gates_json(self, tmp_path):
        import json
        from mode_resolver import set_mode
        result = set_mode("standard", tmp_path)
        assert result.name == "standard"
        config = json.loads((tmp_path / "gates.json").read_text())
        assert config["mode"] == "standard"
