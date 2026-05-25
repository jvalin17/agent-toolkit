"""Config load/save and display helpers for setup_modes."""

from __future__ import annotations

import json
from pathlib import Path

from setup_modes_data import PRESETS, PROFILES, SETTINGS


def load_current_config(project_dir: Path) -> dict:
    """Load current gates.json or return empty dict."""
    gates_path = project_dir / "gates.json"
    if gates_path.is_file():
        try:
            return json.loads(gates_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def write_config(config: dict, project_dir: Path) -> None:
    """Write config to gates.json."""
    gates_path = project_dir / "gates.json"
    gates_path.write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )


def build_full_config(settings: dict) -> dict:
    """Build complete gates.json from flat settings dict."""
    return {
        "gate_mode": "legacy",
        "enforcement": settings.get("enforcement", "block"),
        "profile": settings.get("profile", "minimal"),
        "mode": settings.get("mode", "normal"),
        "eval_threshold": settings.get("eval_threshold", 95),
        "max_session_minutes": settings.get("max_session_minutes", 0),
        "auto": settings.get("auto", False),
        "continue": settings.get("continue", False),
        "tdd": settings.get("tdd", True),
        "tdd_mode": settings.get("tdd_mode", "remind"),
        "skill_routing": settings.get("skill_routing", True),
        "model": settings.get("model", "auto"),
        "gate_protect": settings.get("gate_protect", True),
        "report_protect": settings.get("report_protect", True),
        "profiles": PROFILES,
    }


def apply_preset(preset_name: str, project_dir: Path) -> dict:
    """Apply a named preset to gates.json. Returns the config."""
    config = build_full_config(PRESETS[preset_name])
    write_config(config, project_dir)
    return config


def apply_overrides(overrides: dict, project_dir: Path) -> dict:
    """Merge overrides into existing gates.json (or create from balanced defaults)."""
    current = load_current_config(project_dir)
    if not current:
        current = build_full_config(PRESETS["balanced"])
    current.update(overrides)
    if "profiles" not in current:
        current["profiles"] = PROFILES
    write_config(current, project_dir)
    return current


def format_value(key: str, value) -> str:
    """Format a config value for display."""
    if isinstance(value, bool):
        return "on" if value else "off"
    if key == "max_session_minutes":
        return "none" if value == 0 else f"{value}m"
    if key == "mode":
        return "on" if value == "strict" else "off"
    return str(value)


def show_status(project_dir: Path) -> None:
    """Print current configuration."""
    config = load_current_config(project_dir)
    if not config:
        print(f"No gates.json found in {project_dir}")
        return

    print(f"\n=== Current Configuration ({project_dir / 'gates.json'}) ===\n")
    for setting in SETTINGS:
        key = setting["key"]
        value = config.get(key, "not set")
        label = setting["label"]
        display = format_value(key, value)
        print(f"  {label:<22} {display}")
    print()


def show_confirmation(config: dict) -> None:
    """Print config summary for confirmation."""
    print("\n--- Your configuration ---\n")
    for setting in SETTINGS:
        key = setting["key"]
        value = config.get(key, PRESETS["balanced"].get(key))
        label = setting["label"]
        display = format_value(key, value)
        print(f"  {label:<22} {display}")
    print()
