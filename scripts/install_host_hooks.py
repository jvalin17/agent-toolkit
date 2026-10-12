#!/usr/bin/env python3
"""Install host-specific hook config into a project (Phase B).

Usage:
  python3 scripts/install_host_hooks.py --host cursor --project /path/to/proj
  python3 scripts/install_host_hooks.py --host gemini --project .
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLKIT_ROOT / "hooks"))
sys.path.insert(0, str(TOOLKIT_ROOT / "scripts"))

from config_generator import (  # noqa: E402
    GENERATORS,
    SUPPORTED_TOOLS,
    collect_toolkit_hooks,
)
from host_config import load_host_config  # noqa: E402


HOST_DEST = {
    "cursor": ".cursor/hooks.json",
    "codex-cli": ".codex/config.toml",
    "grok-build": ".grok/hooks.json",
    "windsurf": ".windsurf/hooks.json",
}


def install_host_hooks(host: str, project_dir: Path, toolkit_root: Path = TOOLKIT_ROOT) -> dict:
    project_dir = Path(project_dir).resolve()
    project_dir.mkdir(parents=True, exist_ok=True)
    toolkit_root = Path(toolkit_root).resolve()

    cfg = load_host_config(host)
    written = []

    if host == "claude-code":
        return {
            "ok": False,
            "error": "Use ./install.sh for Claude Code (global ~/.claude)",
        }

    if cfg.get("hooks") == "cli_only" or host == "gemini" or host not in HOST_DEST:
        marker = project_dir / ".agent-toolkit" / "CLI_ONLY.md"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            f"# Host `{host}` is CLI-only\n\n"
            f"Foolproof commits:\n\n"
            f"```bash\n"
            f"python3 {toolkit_root}/scripts/atk.py commit -m \"message\"\n"
            f"```\n\n"
            f"Or: `python3 {toolkit_root}/scripts/atk.py wrap` then use `atk-git`.\n",
            encoding="utf-8",
        )
        written.append(str(marker))
        from generate_project_rules import generate_for_project

        rules = generate_for_project(project_dir, host_id=host, toolkit_root=toolkit_root)
        written.extend(rules.get("written") or [])
        return {"ok": True, "host": host, "mode": "cli_only", "written": written}

    if host not in SUPPORTED_TOOLS or host not in GENERATORS:
        return {"ok": False, "error": f"unsupported host: {host}"}

    hooks = collect_toolkit_hooks(toolkit_root)
    content = GENERATORS[host](hooks, toolkit_root)
    if str(toolkit_root) not in content:
        return {"ok": False, "error": "generated hooks missing absolute toolkit path"}

    dest = project_dir / HOST_DEST[host]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    written.append(str(dest))

    from generate_project_rules import generate_for_project

    rules = generate_for_project(project_dir, host_id=host, toolkit_root=toolkit_root)
    written.extend(rules.get("written") or [])
    return {"ok": True, "host": host, "mode": "structural", "written": written, "config": cfg.get("id")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--project", default=".")
    parser.add_argument("--toolkit", default=str(TOOLKIT_ROOT))
    args = parser.parse_args(argv)
    result = install_host_hooks(args.host, Path(args.project), Path(args.toolkit))
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
