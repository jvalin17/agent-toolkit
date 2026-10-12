"""atk CLI — Phase C foolproof commit wrapper."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "hooks"))

from atk import gate_ready, cmd_status, main as atk_main


def _proj(tmp_path: Path) -> Path:
    (tmp_path / "gates.json").write_text(
        json.dumps({"mode": "default", "gate_mode": "legacy"})
    )
    return tmp_path


def test_gate_ready_false_without_flag(tmp_path):
    project = _proj(tmp_path)
    ok, missing = gate_ready(project, "commit")
    assert ok is False
    assert any("precommit" in m for m in missing)


def test_gate_ready_false_with_corrupt_config(tmp_path):
    """Gemini/Codex/Grok go through atk — a corrupt gates.json must fail closed there too."""
    (tmp_path / "gates.json").write_text('{"mode": "minimal",')
    ok, missing = gate_ready(tmp_path, "commit")
    assert ok is False
    assert len(missing) == 1
    assert "gates.json" in missing[0]
    assert "fail closed" in missing[0]


def test_gate_ready_true_with_ready_flag(tmp_path):
    project = _proj(tmp_path)
    gates = project / ".gates"
    gates.mkdir()
    (gates / "precommit-passed").write_text("READY\n")
    ok, missing = gate_ready(project, "commit")
    assert ok is True
    assert missing == []


def test_atk_commit_blocked_exits_1(tmp_path):
    project = _proj(tmp_path)
    code = atk_main(["--project", str(project), "commit", "-m", "x"])
    assert code == 1
