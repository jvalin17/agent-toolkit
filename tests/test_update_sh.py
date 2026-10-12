"""update.sh — pulling the toolkit from the network is opt-in, not a default."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sandbox(tmp_path: Path) -> tuple[Path, Path, dict]:
    """Copy update.sh next to a stub install.sh and shim `git` on PATH."""
    toolkit = tmp_path / "toolkit"
    toolkit.mkdir(parents=True)
    shutil.copy(ROOT / "update.sh", toolkit / "update.sh")
    (toolkit / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n")

    shim_dir = tmp_path / "bin"
    shim_dir.mkdir(parents=True)
    log = tmp_path / "git-calls.log"
    shim = shim_dir / "git"
    shim.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" >> '{log}'\n"
        "case \"$*\" in\n"
        "  *rev-parse*) printf 'abc123\\n' ;;\n"
        "  *pull*) printf 'Already up to date.\\n' ;;\n"
        "esac\n"
        "exit 0\n"
    )
    shim.chmod(shim.stat().st_mode | stat.S_IEXEC)
    env = {**os.environ, "PATH": f"{shim_dir}:{os.environ['PATH']}"}
    env.pop("AGENT_TOOLKIT_AUTO_PULL", None)
    return toolkit, log, env


def _run(toolkit: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(toolkit / "update.sh")], env=env, capture_output=True, text=True, timeout=60,
    )


def test_no_pull_without_opt_in(tmp_path):
    toolkit, log, env = _sandbox(tmp_path)
    proc = _run(toolkit, env)
    assert proc.returncode == 0, proc.stderr
    calls = log.read_text() if log.exists() else ""
    assert "pull" not in calls
    assert "AGENT_TOOLKIT_AUTO_PULL" in proc.stderr  # tells the user how to enable it


def test_pull_when_opted_in(tmp_path):
    toolkit, log, env = _sandbox(tmp_path)
    env["AGENT_TOOLKIT_AUTO_PULL"] = "1"
    proc = _run(toolkit, env)
    assert proc.returncode == 0, proc.stderr
    assert "pull --ff-only" in log.read_text()


def test_explicit_off_values_do_not_pull(tmp_path):
    for value in ("0", "false", "no", "yes-please"):
        toolkit, log, env = _sandbox(tmp_path / value.replace("-", "_"))
        env["AGENT_TOOLKIT_AUTO_PULL"] = value
        _run(toolkit, env)
        calls = log.read_text() if log.exists() else ""
        assert "pull" not in calls, value
