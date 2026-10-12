"""Tests for hooks/host_config.py — load/merge host configs + resolve_host."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from host_config import (
    HOSTS_DIR,
    deep_merge,
    list_hosts,
    load_host_file,
    load_host_config,
    resolve_host,
    render_bootstrap,
)


class TestDeepMerge:
    def test_host_overrides_scalar(self):
        base = {"id": "default", "hooks": "cli_only", "bootstrap": {"max_chars": 4000}}
        override = {"id": "cursor", "hooks": "structural"}
        merged = deep_merge(base, override)
        assert merged["id"] == "cursor"
        assert merged["hooks"] == "structural"
        assert merged["bootstrap"]["max_chars"] == 4000

    def test_nested_dict_merge(self):
        base = {"bootstrap": {"inject": ["a"], "max_chars": 4000}}
        override = {"bootstrap": {"inject": ["b", "c"]}}
        merged = deep_merge(base, override)
        assert merged["bootstrap"]["inject"] == ["b", "c"]
        assert merged["bootstrap"]["max_chars"] == 4000

    def test_does_not_mutate_inputs(self):
        base = {"a": {"x": 1}}
        override = {"a": {"y": 2}}
        deep_merge(base, override)
        assert base == {"a": {"x": 1}}


class TestLoadHostConfig:
    def test_default_file_exists(self):
        assert (HOSTS_DIR / "default.json").is_file()

    def test_all_required_hosts_exist(self):
        required = [
            "default",
            "claude-code",
            "cursor",
            "codex-cli",
            "gemini",
            "grok-build",
            "windsurf",
        ]
        for name in required:
            assert (HOSTS_DIR / f"{name}.json").is_file(), f"missing hosts/{name}.json"

    def test_list_hosts_includes_cursor(self):
        names = list_hosts()
        assert "cursor" in names
        assert "default" not in names  # default is base, not a selectable host id list exclusive
        # Actually list_hosts should list all including default or excluding?
        # Spec: list selectable hosts — exclude default from list_hosts
        assert "gemini" in names

    def test_load_cursor_merges_default(self):
        cfg = load_host_config("cursor")
        assert cfg["id"] == "cursor"
        assert "rules_targets" in cfg
        assert "bootstrap" in cfg
        assert "max_chars" in cfg["bootstrap"]
        assert "pull" in cfg

    def test_unknown_host_uses_default_with_unknown_id(self):
        cfg = load_host_config("not-a-real-host")
        assert cfg["id"] == "unknown"
        assert "bootstrap" in cfg

    def test_load_host_file_raises_on_missing_default(self, tmp_path, monkeypatch):
        monkeypatch.setattr("host_config.HOSTS_DIR", tmp_path)
        with pytest.raises(FileNotFoundError):
            load_host_file("default")


class TestResolveHost:
    def test_resolve_uses_detect_override(self):
        with patch.dict(os.environ, {"AGENT_TOOLKIT_TOOL": "gemini"}, clear=True):
            cfg = resolve_host()
            assert cfg["id"] == "gemini"

    def test_resolve_unknown_when_no_signals(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("host_config.detect_agent", return_value="unknown"):
                cfg = resolve_host()
                assert cfg["id"] == "unknown"


class TestRenderBootstrap:
    def test_bootstrap_capped_and_non_empty(self):
        cfg = load_host_config("cursor")
        text = render_bootstrap(cfg, toolkit_root=ROOT)
        assert len(text) > 50
        assert len(text) <= cfg["bootstrap"]["max_chars"]
        assert "pull" in text.lower() or "get_skill" in text.lower() or "TDD" in text

    def test_bootstrap_includes_host_id(self):
        cfg = load_host_config("gemini")
        text = render_bootstrap(cfg, toolkit_root=ROOT)
        assert "gemini" in text.lower()
