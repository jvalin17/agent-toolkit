"""JWT issue/verify and gates.json policy."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import jwt

from gate.keys import load_signing_secret

ISSUER = "https://agent-toolkit.gate/local"
ALGORITHM = "HS256"
TOKEN_TYP = "GATE+JWT"


def find_gates_config(project_root: Path) -> Path | None:
    for candidate in (
        project_root / "gates.json",
        project_root / ".claude" / "gates.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def load_gates_config(project_root: Path) -> dict[str, Any]:
    path = find_gates_config(project_root)
    if not path:
        return {
            "gate_mode": "legacy",
            "profile": "standard",
            "eval_threshold": 95,
            "commit_requires": ["precommit"],
            "push_requires": ["evaluate"],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_profile(config: dict[str, Any]) -> str:
    return config.get("profile") or "standard"


def required_skills(config: dict[str, Any], action: str) -> list[str]:
    profile = resolve_profile(config)
    profiles = config.get("profiles") or {}
    if profile in profiles:
        key = f"{action}_requires"
        return list(profiles[profile].get(key, []))
    return list(config.get(f"{action}_requires", []))


def eval_threshold(config: dict[str, Any]) -> int:
    return int(config.get("eval_threshold", 95))


def skill_passed_in_attestation(results: dict[str, Any], skill: str, threshold: int) -> tuple[bool, str]:
    block = results.get(skill)
    if not block:
        return False, f"missing results.{skill}"
    if not block.get("passed"):
        return False, f"{skill} not passed"
    if skill == "evaluate":
        score = block.get("overall_score")
        if score is None:
            return False, "evaluate missing overall_score"
        if int(score) < threshold:
            return False, f"evaluate score {score} < {threshold}"
    return True, "ok"


def gates_claims_from_attestation(
    attestation: dict[str, Any],
    config: dict[str, Any],
    action: str,
) -> dict[str, Any]:
    results = attestation.get("results") or {}
    threshold = eval_threshold(config)
    required = required_skills(config, action)
    gates: dict[str, Any] = {}
    for skill in required:
        ok, _ = skill_passed_in_attestation(results, skill, threshold)
        gates[skill] = {
            "status": "passed" if ok else "failed",
            **(results.get(skill) or {}),
        }
    return gates


def issue_token(
    attestation: dict[str, Any],
    config: dict[str, Any],
    action: str,
    project_root: Path,
    signing_key_path: Path | None = None,
    kid: str = "gate-1",
    ttl_seconds: int = 14400,
) -> str:
    secret = load_signing_secret(project_root, signing_key_path)
    now = int(time.time())
    gates = gates_claims_from_attestation(attestation, config, action)
    if any(g.get("status") != "passed" for g in gates.values()):
        failed = [k for k, v in gates.items() if v.get("status") != "passed"]
        raise ValueError(f"cannot issue token: failed gates {failed}")

    payload = {
        "iss": ISSUER,
        "sub": "gate-bundle",
        "aud": attestation.get("repo", "local/unknown"),
        "iat": now,
        "exp": now + ttl_seconds,
        "jti": str(uuid.uuid4()),
        "typ": TOKEN_TYP,
        "repo": attestation.get("repo"),
        "commit_sha": attestation.get("commit_sha"),
        "ref": attestation.get("ref"),
        "profile": resolve_profile(config),
        "action": action,
        "gates": gates,
        "attestation_producer": attestation.get("producer"),
    }
    headers = {"kid": kid, "typ": TOKEN_TYP, "alg": ALGORITHM}
    return jwt.encode(payload, secret, algorithm=ALGORITHM, headers=headers)


def _looks_like_jwt(token: str) -> bool:
    parts = token.strip().split(".")
    return len(parts) == 3 and all(parts)


def verify_token(
    token: str,
    project_root: Path,
    action: str,
    commit_sha: str | None = None,
    signing_key_path: Path | None = None,
) -> tuple[bool, str]:
    config = load_gates_config(project_root)
    mode = config.get("gate_mode", "legacy")
    # CI and local issue_token always pass a JWT; legacy mode still uses .gates/ flags only
    # when there is no JWT (e.g. hook-less checks). Do not ignore a valid gate-token.jwt.
    if mode == "legacy" and not _looks_like_jwt(token):
        return _verify_legacy(project_root, action, config)
    return _verify_jwt(token, project_root, action, config, commit_sha, signing_key_path)


def _verify_jwt(
    token: str,
    project_root: Path,
    action: str,
    config: dict[str, Any],
    commit_sha: str | None,
    signing_key_path: Path | None,
) -> tuple[bool, str]:
    try:
        secret = load_signing_secret(project_root, signing_key_path)
    except FileNotFoundError as exc:
        return False, str(exc)

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            options={"require": ["exp", "iat"], "verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        return False, f"token invalid: {exc}"

    if commit_sha and payload.get("commit_sha") != commit_sha:
        return (
            False,
            f"token commit_sha mismatch (token={payload.get('commit_sha')}, head={commit_sha})",
        )

    if "gates" not in payload:
        return False, "token missing gates claim"

    required = required_skills(config, action)
    threshold = eval_threshold(config)
    token_gates = payload.get("gates") or {}
    missing = []
    for skill in required:
        block = token_gates.get(skill)
        if not block or block.get("status") != "passed":
            missing.append(skill)
            continue
        if skill == "evaluate":
            score = block.get("overall_score", 0)
            if int(score) < threshold:
                missing.append(f"{skill}({score}%<{threshold}%)")

    if missing:
        return False, f"token missing passed gates: {', '.join(missing)}"

    return True, "ok"


def _verify_legacy(project_root: Path, action: str, config: dict[str, Any]) -> tuple[bool, str]:
    required = required_skills(config, action)
    missing = []
    for skill in required:
        flag = project_root / ".gates" / f"{skill}-passed"
        if not flag.is_file():
            missing.append(skill)
            continue
        text = flag.read_text(encoding="utf-8")
        if skill == "precommit" and "READY" not in text:
            missing.append(f"{skill}(no READY)")
        elif skill == "evaluate":
            if "PASSED" not in text:
                missing.append(skill)
            else:
                import re

                m = re.search(r"(\d+)", text)
                score = int(m.group(1)) if m else 0
                if score < eval_threshold(config):
                    missing.append(f"{skill}({score}%)")
        elif skill in ("reviewer", "assess") and "PASSED" not in text:
            missing.append(skill)
    if missing:
        return False, f"legacy gates missing: {', '.join(missing)}"
    return True, "ok"


def write_token(path: Path, token: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token.strip() + "\n", encoding="utf-8")


def read_token(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def signing_secret_from_env() -> str | None:
    for var in ("AGENT_TOOLKIT_GATE_SECRET", "AGENT_TOOLKIT_GATE_PRIVATE_KEY"):
        val = os.environ.get(var, "").strip()
        if val and not val.startswith("-----"):
            return val
    path = os.environ.get("AGENT_TOOLKIT_GATE_SECRET_FILE", "").strip()
    if not path:
        path = os.environ.get("AGENT_TOOLKIT_GATE_PRIVATE_KEY_FILE", "").strip()
    if path and Path(path).is_file():
        text = Path(path).read_text(encoding="utf-8").strip()
        if text and not text.startswith("-----"):
            return text
    return None
