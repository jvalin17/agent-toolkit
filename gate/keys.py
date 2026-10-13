"""HS256 signing secret for gate tokens (stdlib only — no cryptography wheel).

Key location: **outside the worktree**, under ~/.agent-toolkit/keys/<project-id>/,
mode 0600. A key inside the repo is readable by any agent working in it and
lets that agent mint its own gate tokens. CI uses AGENT_TOOLKIT_GATE_SECRET
instead of a file. The legacy in-repo .gate/signing.key is still read so
existing projects keep working, but new keys are never written there.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path

MIN_SECRET_CHARS = 32
LEGACY_PROJECT_KEYS = (Path(".gate/signing.key"), Path(".gate/private.pem"))
KEYS_HOME_RELATIVE = Path(".agent-toolkit") / "keys"
SECRET_FILE_ENV_VARS = ("AGENT_TOOLKIT_GATE_SECRET_FILE", "AGENT_TOOLKIT_GATE_PRIVATE_KEY_FILE")


def project_key_dir(project_root: Path | None = None) -> Path:
    root = Path(project_root or Path.cwd()).resolve()
    project_id = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16]
    return Path.home() / KEYS_HOME_RELATIVE / project_id


def default_key_path(project_root: Path | None = None) -> Path:
    return project_key_dir(project_root) / "signing.key"


def _write_secret_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def generate_signing_secret(
    signing_key_path: Path | None = None,
    meta_path: Path | None = None,
    project_root: Path | None = None,
) -> Path:
    """Create a random signing secret (0600 from creation). Default path is under HOME."""
    key_path = Path(signing_key_path).resolve() if signing_key_path else default_key_path(project_root)
    meta = Path(meta_path).resolve() if meta_path else key_path.parent / "signing.meta.json"
    _write_secret_file(key_path, secrets.token_urlsafe(48) + "\n")
    meta.parent.mkdir(parents=True, exist_ok=True)
    meta.write_text(
        json.dumps({"alg": "HS256", "kid": "gate-1", "version": 1,
                    "project": str(Path(project_root or Path.cwd()).resolve())}, indent=2) + "\n",
        encoding="utf-8",
    )
    return key_path


def _validated(secret: str, source: str) -> str:
    secret = secret.strip()
    if len(secret) < MIN_SECRET_CHARS:
        raise ValueError(f"signing secret from {source} is shorter than {MIN_SECRET_CHARS} chars — regenerate it")
    return secret


def load_signing_secret(
    project_root: Path | None = None,
    signing_key_path: Path | None = None,
) -> str:
    """Resolve the secret: env value → env file → explicit path → ~/.agent-toolkit/keys → legacy .gate/.

    Raises FileNotFoundError when nothing is found and ValueError when the
    secret is too short (both make verification fail closed).
    """
    env = os.environ.get("AGENT_TOOLKIT_GATE_SECRET", "").strip()
    if env:
        return _validated(env, "AGENT_TOOLKIT_GATE_SECRET")
    legacy_env = os.environ.get("AGENT_TOOLKIT_GATE_PRIVATE_KEY", "").strip()
    if legacy_env and not legacy_env.startswith("-----"):
        return _validated(legacy_env, "AGENT_TOOLKIT_GATE_PRIVATE_KEY")

    root = Path(project_root or Path.cwd())
    candidates: list[Path] = []
    for var in SECRET_FILE_ENV_VARS:
        env_path = os.environ.get(var, "").strip()
        if env_path:
            candidates.append(Path(env_path))
    if signing_key_path is not None:
        p = Path(signing_key_path)
        candidates.append(p if p.is_absolute() else root / p)
    candidates.append(default_key_path(root))
    candidates.extend(root / legacy for legacy in LEGACY_PROJECT_KEYS)

    for path in candidates:
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            if text and not text.startswith("-----"):
                return _validated(text, str(path))
    raise FileNotFoundError(
        f"no signing key at {default_key_path(root)} — run scripts/setup-signed-gates.sh "
        "or set AGENT_TOOLKIT_GATE_SECRET"
    )
