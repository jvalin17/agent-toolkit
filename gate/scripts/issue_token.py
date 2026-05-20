#!/usr/bin/env python3
"""Issue signed gate JWT from attestation.json (CI only — needs private key)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

GATE_PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GATE_PKG.parent))


def _default_project_root() -> Path:
    if (GATE_PKG.parent / "config.json").is_file():
        return GATE_PKG.parent.parent
    return Path.cwd()

from gate.attest import load_attestation  # noqa: E402
from gate.core import (  # noqa: E402
    issue_token,
    load_gates_config,
    signing_secret_from_env,
    write_token,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue agent-toolkit gate JWT")
    parser.add_argument("--project-root", type=Path, default=None)
    parser.add_argument(
        "--attestation",
        type=Path,
        default=Path(".gate/attestation.json"),
    )
    parser.add_argument(
        "--action",
        choices=["commit", "push", "merge"],
        default="push",
    )
    parser.add_argument(
        "--signing-key",
        type=Path,
        default=Path(".gate/signing.key"),
    )
    parser.add_argument("--output", type=Path, default=Path(".gate/gate-token.jwt"))
    args = parser.parse_args()

    project_root = (args.project_root or _default_project_root()).resolve()
    if not args.attestation.is_file():
        print(f"Missing {args.attestation} — run verify_gate.py attest first", file=sys.stderr)
        return 1

    secret = signing_secret_from_env()
    signing_path = args.signing_key
    if secret:
        # Sync gitignored key file to CI secret (bootstrap may have generated a different local key)
        signing_path.parent.mkdir(parents=True, exist_ok=True)
        signing_path.write_text(secret.strip() + "\n", encoding="utf-8")
        signing_path.chmod(0o600)

    if not signing_path.is_file() and not secret:
        print(
            "Missing signing secret. Set AGENT_TOOLKIT_GATE_SECRET (GitHub secret) "
            f"or {signing_path} (gitignored, created by install.sh)",
            file=sys.stderr,
        )
        return 1

    attestation = load_attestation(args.attestation)
    config = load_gates_config(project_root)
    try:
        token = issue_token(attestation, config, args.action, project_root, signing_path)
    except ValueError as exc:
        print(f"Cannot issue token: {exc}", file=sys.stderr)
        return 1

    write_token(args.output, token)
    print(f"Issued gate token → {args.output}")
    print(json.dumps({"action": args.action, "commit_sha": attestation.get("commit_sha")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
