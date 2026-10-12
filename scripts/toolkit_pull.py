#!/usr/bin/env python3
"""CLI twin of MCP pull tools for hosts without MCP.

Usage:
  python3 scripts/toolkit_pull.py resolve_host
  python3 scripts/toolkit_pull.py get_skill implementation
  python3 scripts/toolkit_pull.py get_module implementation tdd
  python3 scripts/toolkit_pull.py run_function gate_status --project .
  python3 scripts/toolkit_pull.py bootstrap [--host cursor]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLKIT_ROOT / "hooks"))

from host_config import load_host_config, render_bootstrap, resolve_host  # noqa: E402
from skill_pull import get_module, get_skill, run_function, stamp_skill  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pull toolkit skills/modules/functions")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("resolve_host")

    p_boot = sub.add_parser("bootstrap")
    p_boot.add_argument("--host", default=None)

    p_skill = sub.add_parser("get_skill")
    p_skill.add_argument("name")

    p_mod = sub.add_parser("get_module")
    p_mod.add_argument("skill")
    p_mod.add_argument("module")

    p_fn = sub.add_parser("run_function")
    p_fn.add_argument("name")
    p_fn.add_argument("--project", default=".")

    p_stamp = sub.add_parser("stamp_skill")
    p_stamp.add_argument("name")
    p_stamp.add_argument("--project", default=".")

    args = parser.parse_args(argv)

    if args.cmd == "resolve_host":
        print(json.dumps(resolve_host(), indent=2))
    elif args.cmd == "bootstrap":
        cfg = load_host_config(args.host) if args.host else resolve_host()
        print(render_bootstrap(cfg, toolkit_root=TOOLKIT_ROOT))
    elif args.cmd == "get_skill":
        print(json.dumps(get_skill(args.name, toolkit_root=TOOLKIT_ROOT), indent=2))
    elif args.cmd == "get_module":
        print(json.dumps(get_module(args.skill, args.module, toolkit_root=TOOLKIT_ROOT), indent=2))
    elif args.cmd == "run_function":
        print(json.dumps(
            run_function(args.name, {"project_dir": args.project}, toolkit_root=TOOLKIT_ROOT),
            indent=2,
        ))
    elif args.cmd == "stamp_skill":
        print(json.dumps(stamp_skill(args.name, Path(args.project)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
