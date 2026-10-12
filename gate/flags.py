"""HMAC-signed gate flags (.gates/<skill>-passed) — stdlib only.

A flag is two lines: the content finalize wrote, then `sig:<hmac-sha256>`.
The MAC covers the project path, the skill and the content, with a key kept
*outside* the worktree (default ~/.agent-toolkit/flag.key, mode 0600). A
`touch .gates/precommit-passed` or a hand-written READY no longer unlocks a
gate; the agent would have to read the key, and path protection denies the
obvious ways of doing that.

Trust boundary (be honest about it): on a single-user machine an agent with
unrestricted shell access can eventually read any file the user can. These
flags stop drift and casual forgery. Against a determined hostile agent the
backstop is signed mode with the secret held in CI, not on the machine.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from pathlib import Path
from typing import Tuple

FLAG_KEY_ENV = "AGENT_TOOLKIT_FLAG_KEY_FILE"
DEFAULT_KEY_RELATIVE = Path(".agent-toolkit") / "flag.key"
SIG_PREFIX = "sig:"
MIN_KEY_CHARS = 32


def flag_key_path() -> Path:
    """Key location: $AGENT_TOOLKIT_FLAG_KEY_FILE, else ~/.agent-toolkit/flag.key."""
    override = os.environ.get(FLAG_KEY_ENV, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / DEFAULT_KEY_RELATIVE


def _create_key(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_urlsafe(48)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, (secret + "\n").encode("utf-8"))
    finally:
        os.close(fd)
    return secret


def _load_key(create: bool) -> str | None:
    path = flag_key_path()
    if path.is_file():
        text = path.read_text(encoding="utf-8").strip()
        return text if len(text) >= MIN_KEY_CHARS else None
    if not create:
        return None
    try:
        return _create_key(path)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()


def _mac(key: str, project_dir: Path, skill: str, content: str) -> str:
    message = "\0".join((str(Path(project_dir).resolve()), skill, content)).encode("utf-8")
    return hmac.new(key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _flag_path(project_dir: Path, skill: str) -> Path:
    return Path(project_dir) / ".gates" / f"{skill}-passed"


def write_flag(project_dir: Path, skill: str, content: str) -> Path:
    """Write a signed flag. Creates the key on first use."""
    key = _load_key(create=True)
    if key is None:
        raise RuntimeError(f"flag key at {flag_key_path()} is too short; delete it to regenerate")
    content = content.strip()
    path = _flag_path(project_dir, skill)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content}\n{SIG_PREFIX}{_mac(key, project_dir, skill, content)}\n", encoding="utf-8")
    return path


def sign_flag_file(path: Path, content: str) -> Path:
    """Sign a flag at an explicit path (project is the parent of .gates/). For tests and tooling."""
    path = Path(path)
    skill = path.name.removesuffix("-passed")
    return write_flag(path.parent.parent, skill, content)


def verify_flag(project_dir: Path, skill: str) -> Tuple[bool, str, str]:
    """(ok, content, reason). Content is returned even when not ok, for messages."""
    path = _flag_path(project_dir, skill)
    if not path.is_file():
        return False, "", "missing"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return False, "", f"unreadable ({exc})"
    content = lines[0].strip() if lines else ""
    sig_line = next((ln.strip() for ln in lines[1:] if ln.startswith(SIG_PREFIX)), None)
    if sig_line is None:
        return False, content, "unsigned — written outside finalize_report"
    key = _load_key(create=False)
    if key is None:
        return False, content, f"flag key missing or too short at {flag_key_path()}"
    expected = _mac(key, project_dir, skill, content)
    if not hmac.compare_digest(sig_line[len(SIG_PREFIX):], expected):
        return False, content, "signature mismatch — flag was altered or forged"
    return True, content, "ok"
