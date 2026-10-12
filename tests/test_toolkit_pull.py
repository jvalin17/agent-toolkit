"""scripts/toolkit_pull.py — CLI twin of the MCP pull tools (Gemini, Codex, Grok, ...)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "toolkit_pull.py"


def _run(*args, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30, cwd=ROOT, env=env,
    )


def test_get_skill_cli():
    proc = _run("get_skill", "precommit")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["name"] == "precommit"
    assert "finalize_report.py" in data["stub"]
    assert isinstance(data["modules"], list)


def test_get_skill_unknown():
    proc = _run("get_skill", "no-such-skill")
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == {"error": "Unknown skill: no-such-skill"}


def test_get_module_rejects_traversal():
    proc = _run("get_module", "implementation", "../../gates")
    assert json.loads(proc.stdout) == {"error": "Invalid module name"}


def test_run_function_gate_status(tmp_path):
    (tmp_path / "gates.json").write_text(json.dumps({"mode": "default", "gate_mode": "legacy"}))
    proc = _run("run_function", "gate_status", "--project", str(tmp_path))
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["ok"] is True
    assert data["ready"] is False
    assert "precommit" in " ".join(str(m) for m in data["missing"])


def test_stamp_skill_cli_writes_json_stamp(tmp_path):
    proc = _run("stamp_skill", "reviewer", "--project", str(tmp_path))
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["ok"] is True
    stamp = json.loads((tmp_path / ".gates" / "stamps" / "reviewer").read_text())
    assert stamp["skill"] == "reviewer"
    assert stamp["source"] == "cli"


@pytest.mark.parametrize("bad_name", ["../../escaped", "not-a-skill"])
def test_stamp_skill_cli_rejects_bad_names(tmp_path, bad_name):
    proc = _run("stamp_skill", bad_name, "--project", str(tmp_path))
    data = json.loads(proc.stdout)
    assert data["ok"] is False
    assert not (tmp_path / "escaped").exists()


def test_resolve_host_honours_tool_override():
    import os

    env = {**os.environ, "AGENT_TOOLKIT_TOOL": "gemini"}
    env.pop("CLAUDECODE", None)
    proc = _run("resolve_host", env=env)
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["id"] == "gemini"
    assert data["stamp_mode"] == "cli_stamp"


def test_bootstrap_for_cursor_mentions_stamp_mode():
    proc = _run("bootstrap", "--host", "cursor")
    assert proc.returncode == 0
    assert "cli_stamp" in proc.stdout
