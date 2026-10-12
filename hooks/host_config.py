"""Load and merge per-LLM host configuration (LLM-agnostic modular toolkit).

Host files live in toolkit `hosts/*.json`. Every host merges over `default.json`.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

TOOLKIT_ROOT = Path(__file__).resolve().parents[1]
HOSTS_DIR = TOOLKIT_ROOT / "hosts"

from agent_detect import detect_agent  # noqa: E402


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge override onto base without mutating inputs. Lists/scalars replaced."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def load_host_file(name: str) -> Dict[str, Any]:
    """Load a single hosts/<name>.json. Raises FileNotFoundError if missing."""
    path = HOSTS_DIR / f"{name}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Host config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def list_hosts() -> List[str]:
    """Return selectable host ids (all hosts/*.json except default)."""
    names = []
    if not HOSTS_DIR.is_dir():
        return names
    for path in sorted(HOSTS_DIR.glob("*.json")):
        if path.stem == "default":
            continue
        names.append(path.stem)
    return names


def load_host_config(host_id: str) -> Dict[str, Any]:
    """Merge default ⊕ host. Unknown host → default with id 'unknown'."""
    default_cfg = load_host_file("default")
    if host_id in ("", "unknown", "default"):
        cfg = copy.deepcopy(default_cfg)
        if host_id == "unknown":
            cfg["id"] = "unknown"
        return cfg

    path = HOSTS_DIR / f"{host_id}.json"
    if not path.is_file():
        cfg = copy.deepcopy(default_cfg)
        cfg["id"] = "unknown"
        return cfg

    host_cfg = load_host_file(host_id)
    return deep_merge(default_cfg, host_cfg)


def resolve_host(stdin_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Detect agent and return merged host config."""
    host_id = detect_agent(stdin_payload)
    return load_host_config(host_id)


def _safe_read_rule(toolkit_root: Path, relative: str) -> str:
    """Read a rules file under toolkit_root; reject path escape."""
    root = toolkit_root.resolve()
    target = (root / relative).resolve()
    if not str(target).startswith(str(root)):
        return f"(blocked path: {relative})\n"
    if not target.is_file():
        return f"(missing: {relative})\n"
    return target.read_text(encoding="utf-8")


def render_bootstrap(
    cfg: Dict[str, Any],
    toolkit_root: Optional[Path] = None,
) -> str:
    """Render short bootstrap text from cfg['bootstrap']['inject'], capped by max_chars."""
    root = toolkit_root or TOOLKIT_ROOT
    bootstrap = cfg.get("bootstrap") or {}
    inject = bootstrap.get("inject") or ["rules/core.md"]
    max_chars = int(bootstrap.get("max_chars") or 4000)

    parts: List[str] = [
        f"# Agent Toolkit bootstrap\n",
        f"Host: **{cfg.get('id', 'unknown')}**\n",
        f"Hooks: `{cfg.get('hooks', 'cli_only')}` | Stamp: `{cfg.get('stamp_mode', 'cli_stamp')}`\n",
        f"Pull via: {', '.join(cfg.get('pull') or ['mcp'])}\n",
        "Use `get_skill` / `get_module` / `run_function` — do not guess long workflows.\n\n",
    ]
    for relative in inject:
        parts.append(_safe_read_rule(root, relative))
        parts.append("\n")

    text = "".join(parts)
    if len(text) > max_chars:
        text = text[: max_chars - 20] + "\n\n…[truncated]\n"
    return text
