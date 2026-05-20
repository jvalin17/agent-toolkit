"""HS256 signing secret for gate tokens (stdlib only — no cryptography wheel)."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

DEFAULT_SIGNING_KEY = Path(".gate/signing.key")
META_FILE = Path(".gate/signing.meta.json")
USER_SIGNING_DIR = Path.home() / ".config" / "agent-toolkit" / "gate"
USER_SIGNING_KEY = USER_SIGNING_DIR / "signing.key"
USER_SIGNING_META = USER_SIGNING_DIR / "signing.meta.json"


def user_signing_key_path() -> Path:
    return USER_SIGNING_KEY


def is_shared_signing(config: dict | None = None) -> bool:
    if config and config.get("signing") == "shared":
        return True
    import os

    return os.environ.get("AGENT_TOOLKIT_SIGNING", "").strip().lower() == "shared"


def generate_signing_secret(signing_key_path: Path | None = None, meta_path: Path | None = None) -> Path:
    """Create a random signing secret. Uses only stdlib (no cryptography package)."""
    key_path = signing_key_path or DEFAULT_SIGNING_KEY
    meta = meta_path or META_FILE
    key_path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_urlsafe(48)
    key_path.write_text(secret + "\n", encoding="utf-8")
    key_path.chmod(0o600)
    meta.write_text(
        json.dumps({"alg": "HS256", "kid": "gate-1", "version": 1}, indent=2) + "\n",
        encoding="utf-8",
    )
    return key_path


def load_signing_secret(
    project_root: Path | None = None,
    signing_key_path: Path | None = None,
) -> str:
    import os

    env = os.environ.get("AGENT_TOOLKIT_GATE_SECRET", "").strip()
    if env:
        return env
    # Back-compat with earlier bootstrap name
    legacy = os.environ.get("AGENT_TOOLKIT_GATE_PRIVATE_KEY", "").strip()
    if legacy and not legacy.startswith("-----"):
        return legacy

    root = project_root or Path.cwd()
    config = {}
    gates_file = root / "gates.json"
    if gates_file.is_file():
        try:
            config = json.loads(gates_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            config = {}

    paths: list[Path | None] = [
        signing_key_path,
        root / ".gate/signing.key",
        root / ".gate/private.pem",
    ]
    if is_shared_signing(config) or USER_SIGNING_KEY.is_file():
        paths.append(USER_SIGNING_KEY)

    for name in paths:
        if name is None:
            continue
        path = name if name.is_absolute() else root / name
        if path.is_file():
            text = path.read_text(encoding="utf-8").strip()
            if text and not text.startswith("-----"):
                return text
    raise FileNotFoundError(
        "missing signing key — run scripts/setup-shared-gate.sh once (all repos), "
        "or ./install.sh in project root for per-repo .gate/signing.key"
    )
