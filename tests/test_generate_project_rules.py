"""generate_project_rules writes short AGENTS.md from host bootstrap."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hooks"))

from generate_project_rules import generate_for_project


def test_generates_short_agents_md(tmp_path):
    result = generate_for_project(
        project_dir=tmp_path,
        host_id="cursor",
        toolkit_root=ROOT,
    )
    assert result["ok"] is True
    agents = tmp_path / "AGENTS.md"
    assert agents.is_file()
    text = agents.read_text(encoding="utf-8")
    assert "get_skill" in text or "pull" in text.lower()
    assert "TDD" in text
    # Must not dump full precommit workflow body
    assert "G-PC-1" not in text or len(text) < 8000
    assert len(text) < 8000
    assert len(text) > 100


def test_cursor_writes_rules_mdc(tmp_path):
    generate_for_project(tmp_path, host_id="cursor", toolkit_root=ROOT)
    mdc = tmp_path / ".cursor" / "rules" / "toolkit.mdc"
    assert mdc.is_file()
    body = mdc.read_text(encoding="utf-8")
    assert "alwaysApply" in body or "Agent Toolkit" in body


def test_gemini_writes_gemini_md(tmp_path):
    generate_for_project(tmp_path, host_id="gemini", toolkit_root=ROOT)
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "GEMINI.md").is_file()
