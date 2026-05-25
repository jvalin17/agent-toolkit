#!/usr/bin/env python3
"""Verify signed gate token or run attestation (CI / local)."""

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

from gate.attest import build_attestation, git_head_sha, write_attestation  # noqa: E402
from gate.core import (  # noqa: E402
    load_gates_config,
    read_token,
    verify_token,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent-toolkit gate verification")
    parser.add_argument("--project-root", type=Path, default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    attest_p = sub.add_parser("attest", help="Run mechanical checks, write attestation.json")
    attest_p.add_argument("--project-root", type=Path, default=None)

    verify_p = sub.add_parser("verify", help="Verify gate-token.jwt for action")
    verify_p.add_argument("--project-root", type=Path, default=None)
    verify_p.add_argument("--action", choices=["commit", "push", "merge"], required=True)
    verify_p.add_argument("--token-path", type=Path, default=Path(".gate/gate-token.jwt"))
    verify_p.add_argument("--commit", type=str, default="")

    args = parser.parse_args()
    project_root = (getattr(args, "project_root", None) or _default_project_root()).resolve()

    if args.command == "attest":
        config = load_gates_config(project_root)
        att = build_attestation(project_root, config)
        out = project_root / ".gate" / "attestation.json"
        write_attestation(out, att)
        print(json.dumps(att.to_dict(), indent=2))
        if not att.results.get("precommit", {}).get("passed"):
            return 1
        return 0

    if args.command == "verify":
        token_path = args.token_path
        if not token_path.is_file():
            print(f"BLOCKED: missing {token_path}", file=sys.stderr)
            print(
                "Push your branch and wait for the agent-toolkit-gate CI job, "
                "or run: python gate/scripts/verify_gate.py attest && issue_token.py",
                file=sys.stderr,
            )
            return 1
        commit = args.commit or git_head_sha(project_root)
        ok, msg = verify_token(read_token(token_path), project_root, args.action, commit)
        if not ok:
            print(f"BLOCKED: {msg}", file=sys.stderr)
            return 1
        print(f"OK: {msg}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
