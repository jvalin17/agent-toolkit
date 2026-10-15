"""gate/keys.py — where the HS256 gate secret is resolved from."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate.keys import SECRET_FILE_ENV_VARS, default_key_path, generate_signing_secret, load_signing_secret

SECRET = "q8Zr3vLm1nB7kX2pW9tJ5cH4dF6gY0sA1eR8uI3oP5"


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    for var in ("AGENT_TOOLKIT_GATE_SECRET", "AGENT_TOOLKIT_GATE_PRIVATE_KEY", *SECRET_FILE_ENV_VARS):
        monkeypatch.delenv(var, raising=False)
    return tmp_path / "home"


class TestLoadSigningSecret:
    def test_secret_file_env_var_is_honoured(self, tmp_path, isolated_home, monkeypatch):
        """CI sets AGENT_TOOLKIT_GATE_SECRET_FILE; the single resolver must read it."""
        secret_file = tmp_path / "ci" / "gate.secret"
        secret_file.parent.mkdir()
        secret_file.write_text(SECRET + "\n", encoding="utf-8")
        monkeypatch.setenv("AGENT_TOOLKIT_GATE_SECRET_FILE", str(secret_file))
        assert load_signing_secret(tmp_path / "billing-app") == SECRET

    def test_secret_file_env_var_beats_home_key(self, tmp_path, isolated_home, monkeypatch):
        project = tmp_path / "billing-app"
        project.mkdir()
        generate_signing_secret(project_root=project)
        secret_file = tmp_path / "ci.secret"
        secret_file.write_text(SECRET, encoding="utf-8")
        monkeypatch.setenv("AGENT_TOOLKIT_GATE_SECRET_FILE", str(secret_file))
        assert load_signing_secret(project) == SECRET

    def test_home_key_found_without_any_env(self, tmp_path, isolated_home):
        project = tmp_path / "billing-app"
        project.mkdir()
        key_path = generate_signing_secret(project_root=project)
        assert key_path == default_key_path(project)
        assert str(key_path).startswith(str(isolated_home))
        assert load_signing_secret(project) == key_path.read_text().strip()

    def test_missing_everything_names_the_fix(self, tmp_path, isolated_home):
        with pytest.raises(FileNotFoundError, match="setup-signed-gates.sh"):
            load_signing_secret(tmp_path / "billing-app")

    def test_short_secret_file_rejected(self, tmp_path, isolated_home, monkeypatch):
        secret_file = tmp_path / "weak.secret"
        secret_file.write_text("tooshort", encoding="utf-8")
        monkeypatch.setenv("AGENT_TOOLKIT_GATE_SECRET_FILE", str(secret_file))
        with pytest.raises(ValueError, match="shorter than 32"):
            load_signing_secret(tmp_path / "billing-app")


class TestBootstrapSecretUpload:
    """bootstrap-project-gates.sh uploads the HOME key, not a repo path that no longer exists."""

    def test_upload_sends_home_key_to_gh(self, tmp_path, isolated_home):
        import os
        import subprocess

        isolated_home.mkdir(parents=True, exist_ok=True)
        project = tmp_path / "project"
        project.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)

        # Fake `gh`: auth status succeeds; `secret set` records the name and stdin.
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        received = tmp_path / "received.txt"
        gh = fake_bin / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "auth" ]; then exit 0; fi\n'
            f'if [ "$1" = "secret" ]; then printf "%s\\n" "$3" > "{received}"; cat >> "{received}"; exit 0; fi\n'
            "exit 1\n",
            encoding="utf-8",
        )
        gh.chmod(0o755)

        env = {
            **os.environ,
            "HOME": str(isolated_home),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "AGENT_TOOLKIT_UPLOAD_GATE_SECRET": "1",
        }
        proc = subprocess.run(
            ["bash", str(ROOT / "scripts/bootstrap-project-gates.sh"), str(ROOT), str(project)],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, proc.stderr + proc.stdout
        assert "GitHub secret AGENT_TOOLKIT_GATE_SECRET set" in proc.stdout, proc.stdout

        name, secret = received.read_text(encoding="utf-8").split("\n", 1)
        assert name == "AGENT_TOOLKIT_GATE_SECRET"
        assert secret.strip() == default_key_path(project).read_text(encoding="utf-8").strip()
        assert len(secret.strip()) >= 32
