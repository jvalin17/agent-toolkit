"""Tests for scripts/setup_modes.py — interactive setup wizard and CLI presets."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "hooks"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from setup_modes import (
    PRESETS,
    PROFILES,
    SETTINGS,
    apply_preset,
    apply_overrides,
    show_status,
    write_config,
    parse_args,
)


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


class TestPresets:
    """Preset mappings produce valid gates.json configs."""

    def test_all_presets_exist(self):
        assert set(PRESETS.keys()) == {"quick", "balanced", "guarded", "lockdown"}

    def test_quick_disables_tdd_and_routing(self):
        assert PRESETS["quick"]["tdd"] is False
        assert PRESETS["quick"]["skill_routing"] is False
        assert PRESETS["quick"]["enforcement"] == "warn"

    def test_balanced_enables_tdd_and_routing(self):
        assert PRESETS["balanced"]["tdd"] is True
        assert PRESETS["balanced"]["skill_routing"] is True
        assert PRESETS["balanced"]["enforcement"] == "block"

    def test_guarded_requires_eval_on_push(self):
        assert PRESETS["guarded"]["profile"] == "standard"
        assert PRESETS["guarded"]["enforcement"] == "block"

    def test_lockdown_is_strict_with_all_reviews(self):
        assert PRESETS["lockdown"]["mode"] == "strict"
        assert PRESETS["lockdown"]["profile"] == "paranoid"
        assert PRESETS["lockdown"]["max_session_minutes"] == 70

    def test_all_presets_have_all_settings(self):
        setting_keys = {s["key"] for s in SETTINGS}
        for name, preset in PRESETS.items():
            for key in setting_keys:
                assert key in preset, f"Preset '{name}' missing key '{key}'"


class TestApplyPreset:
    """apply_preset writes correct gates.json."""

    def test_writes_gates_json(self, project_dir):
        apply_preset("quick", project_dir)
        gates_path = project_dir / "gates.json"
        assert gates_path.is_file()
        config = json.loads(gates_path.read_text())
        assert config["tdd"] is False
        assert config["skill_routing"] is False

    def test_preserves_profiles(self, project_dir):
        apply_preset("balanced", project_dir)
        config = json.loads((project_dir / "gates.json").read_text())
        assert "profiles" in config
        assert "minimal" in config["profiles"]
        assert "paranoid" in config["profiles"]

    def test_lockdown_preset(self, project_dir):
        apply_preset("lockdown", project_dir)
        config = json.loads((project_dir / "gates.json").read_text())
        assert config["mode"] == "strict"
        assert config["profile"] == "paranoid"
        assert config["max_session_minutes"] == 70


class TestApplyOverrides:
    """apply_overrides merges CLI flags into existing config."""

    def test_overrides_single_setting(self, project_dir):
        apply_preset("balanced", project_dir)
        apply_overrides({"tdd": False}, project_dir)
        config = json.loads((project_dir / "gates.json").read_text())
        assert config["tdd"] is False
        # Other settings unchanged
        assert config["skill_routing"] is True

    def test_overrides_multiple_settings(self, project_dir):
        apply_preset("quick", project_dir)
        apply_overrides({"model": "sonnet", "max_session_minutes": 30}, project_dir)
        config = json.loads((project_dir / "gates.json").read_text())
        assert config["model"] == "sonnet"
        assert config["max_session_minutes"] == 30

    def test_creates_gates_json_if_missing(self, project_dir):
        apply_overrides({"tdd": False}, project_dir)
        config = json.loads((project_dir / "gates.json").read_text())
        assert config["tdd"] is False


class TestShowStatus:
    """show_status prints current config."""

    def test_shows_config(self, project_dir, capsys):
        apply_preset("guarded", project_dir)
        show_status(project_dir)
        output = capsys.readouterr().out
        assert "guarded" in output.lower() or "standard" in output
        assert "tdd" in output.lower()

    def test_no_gates_json(self, project_dir, capsys):
        show_status(project_dir)
        output = capsys.readouterr().out
        assert "no gates.json" in output.lower() or "not found" in output.lower()


class TestWriteConfig:
    """write_config writes valid JSON."""

    def test_writes_valid_json(self, project_dir):
        config = {"tdd": True, "model": "auto", "profiles": {}}
        write_config(config, project_dir)
        result = json.loads((project_dir / "gates.json").read_text())
        assert result == config

    def test_overwrites_existing(self, project_dir):
        (project_dir / "gates.json").write_text('{"old": true}')
        config = {"tdd": False, "profiles": {}}
        write_config(config, project_dir)
        result = json.loads((project_dir / "gates.json").read_text())
        assert "old" not in result
        assert result["tdd"] is False


class TestParseArgs:
    """CLI argument parsing."""

    def test_preset_flags(self):
        args = parse_args(["--quick"])
        assert args.quick is True

    def test_individual_settings(self):
        args = parse_args(["--tdd", "off", "--model", "sonnet"])
        assert args.tdd == "off"
        assert args.model == "sonnet"

    def test_time_limit(self):
        args = parse_args(["--time-limit", "30"])
        assert args.time_limit == 30

    def test_status_flag(self):
        args = parse_args(["--status"])
        assert args.status is True

    def test_project_dir(self):
        args = parse_args(["--project-dir", "/tmp/test"])
        assert args.project_dir == "/tmp/test"

    def test_no_args_defaults(self):
        args = parse_args([])
        assert args.status is False
        assert args.quick is False
        assert args.tdd is None
