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
from gate.core import issue_token, load_gates_config, write_token  # noqa: E402


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
        default=None,
        help="explicit key file; default: AGENT_TOOLKIT_GATE_SECRET, "
             "~/.agent-toolkit/keys/<project>/, then the legacy in-repo .gate/ key",
    )
    parser.add_argument("--output", type=Path, default=Path(".gate/gate-token.jwt"))
    args = parser.parse_args()

    project_root = (args.project_root or _default_project_root()).resolve()
    if not args.attestation.is_file():
        print(f"Missing {args.attestation} — run verify_gate.py attest first", file=sys.stderr)
        return 1

    attestation = load_attestation(args.attestation)
    config = load_gates_config(project_root)
    try:
        # Key resolution lives in gate.keys: env secret, env file, explicit path,
        # ~/.agent-toolkit/keys/<project>/, legacy in-repo .gate/. The secret is
        # never copied into the worktree.
        token = issue_token(attestation, config, args.action, project_root, args.signing_key)
    except FileNotFoundError as exc:
        print(
            f"Missing signing secret: {exc}. Set AGENT_TOOLKIT_GATE_SECRET (GitHub secret) "
            "or run scripts/setup-signed-gates.sh",
            file=sys.stderr,
        )
        return 1
    except ValueError as exc:
        print(f"Cannot issue token: {exc}", file=sys.stderr)
        return 1

    write_token(args.output, token)
    print(f"Issued gate token → {args.output}")
    print(json.dumps({"action": args.action, "commit_sha": attestation.get("commit_sha")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
