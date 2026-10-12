"""install_host_hooks — Phase B."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hooks"))

from install_host_hooks import install_host_hooks


def test_install_cursor_writes_hooks_with_toolkit_path(tmp_path):
    result = install_host_hooks("cursor", tmp_path, toolkit_root=ROOT)
    assert result["ok"] is True
    assert result["mode"] == "structural"
    hooks = tmp_path / ".cursor" / "hooks.json"
    assert hooks.is_file()
    text = hooks.read_text(encoding="utf-8")
    assert str(ROOT) in text
    assert "gate_hook.py" in text
    assert (tmp_path / "AGENTS.md").is_file()


def test_install_gemini_is_cli_only(tmp_path):
    result = install_host_hooks("gemini", tmp_path, toolkit_root=ROOT)
    assert result["ok"] is True
    assert result["mode"] == "cli_only"
    assert (tmp_path / ".agent-toolkit" / "CLI_ONLY.md").is_file()
    assert (tmp_path / "AGENTS.md").is_file()


def test_install_grok_writes_hooks(tmp_path):
    result = install_host_hooks("grok-build", tmp_path, toolkit_root=ROOT)
    assert result["ok"] is True
    assert (tmp_path / ".grok" / "hooks.json").is_file()
