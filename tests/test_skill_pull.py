"""Tests for hooks/skill_pull.py — get_skill / get_module / run_function / stamp."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from skill_pull import (
    get_skill,
    get_module,
    list_modules,
    run_function,
    stamp_skill,
    FUNCTION_REGISTRY,
)


class TestGetSkill:
    def test_implementation_returns_stub_and_modules(self):
        result = get_skill("implementation", toolkit_root=ROOT)
        assert "error" not in result
        assert "stub" in result
        assert "modules" in result
        assert isinstance(result["modules"], list)
        assert "tdd" in result["modules"] or "full" in result["modules"]
        # stub should be shorter than historical 240-line skill once stubified;
        # until stubified, still returns content
        assert len(result["stub"]) > 20

    def test_unknown_skill(self):
        result = get_skill("not-a-skill", toolkit_root=ROOT)
        assert "error" in result


class TestGetModule:
    def test_fetch_existing_module(self):
        mods = list_modules("implementation", toolkit_root=ROOT)
        assert mods, "implementation should have at least one module after setup"
        name = mods[0]
        result = get_module("implementation", name, toolkit_root=ROOT)
        assert "error" not in result
        assert "content" in result
        assert len(result["content"]) > 10

    def test_path_escape_blocked(self):
        result = get_module("implementation", "../etc/passwd", toolkit_root=ROOT)
        assert "error" in result

    def test_missing_module(self):
        result = get_module("implementation", "no-such-module-xyz", toolkit_root=ROOT)
        assert "error" in result


class TestRunFunction:
    def test_registry_has_required_functions(self):
        assert "check_tdd_order" in FUNCTION_REGISTRY
        assert "gate_status" in FUNCTION_REGISTRY

    def test_unknown_function_rejected(self):
        result = run_function("os_system", {}, toolkit_root=ROOT)
        assert result.get("ok") is False
        assert "error" in result

    def test_gate_status_returns_structure(self, tmp_path):
        result = run_function(
            "gate_status",
            {"project_dir": str(tmp_path)},
            toolkit_root=ROOT,
        )
        assert "ok" in result
        assert "ready" in result
        assert "missing" in result


class TestStampSkill:
    def test_stamp_creates_file(self, tmp_path):
        result = stamp_skill("implementation", project_dir=tmp_path)
        assert result.get("ok") is True
        stamp = tmp_path / ".gates" / "stamps" / "implementation"
        assert stamp.is_file()

    def test_stamp_writes_json_with_cli_source(self, tmp_path):
        stamp_skill("reviewer", project_dir=tmp_path)
        data = json.loads((tmp_path / ".gates" / "stamps" / "reviewer").read_text())
        assert data["skill"] == "reviewer"
        assert data["source"] == "cli"
        assert data["timestamp"].startswith("20")

    @pytest.mark.parametrize("bad_name", [
        "../../escaped",
        "..\\..\\escaped",
        "stamps/../../escaped",
        "/etc/passwd",
        "",
        "..",
    ])
    def test_stamp_rejects_traversal_name(self, tmp_path, bad_name):
        result = stamp_skill(bad_name, project_dir=tmp_path)
        assert result.get("ok") is False
        assert "name" in result.get("error", "").lower()
        assert not (tmp_path / "escaped").exists()
        stamps = tmp_path / ".gates" / "stamps"
        assert not stamps.exists() or list(stamps.iterdir()) == []

    def test_stamp_rejects_unknown_skill(self, tmp_path):
        result = stamp_skill("not-a-real-skill", project_dir=tmp_path)
        assert result.get("ok") is False
        assert "unknown skill" in result.get("error", "").lower()
        assert not (tmp_path / ".gates" / "stamps" / "not-a-real-skill").exists()

    def test_stamp_accepts_plugin_prefixed_skill(self, tmp_path):
        result = stamp_skill("agent-toolkit:precommit", project_dir=tmp_path)
        assert result.get("ok") is True
        assert (tmp_path / ".gates" / "stamps" / "agent-toolkit:precommit").is_file()
