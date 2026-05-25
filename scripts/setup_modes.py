#!/usr/bin/env python3
"""Setup wizard for agent-toolkit modes.

Interactive wizard or CLI one-liners to configure gates.json.
Offers named presets (quick/balanced/guarded/lockdown) as starting
points, with full customization of every setting.

Usage:
    python3 scripts/setup_modes.py                    # interactive wizard
    python3 scripts/setup_modes.py --quick             # preset, no questions
    python3 scripts/setup_modes.py --tdd off --model sonnet  # individual flags
    python3 scripts/setup_modes.py --status            # show current config
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from setup_modes_data import PRESET_DESCRIPTIONS, PRESETS, PROFILES, SETTINGS
from setup_modes_io import (
    apply_overrides,
    apply_preset,
    build_full_config,
    format_value,
    show_confirmation,
    show_status,
    write_config,
)

# Re-export for tests
__all__ = [
    "PRESETS",
    "PROFILES",
    "SETTINGS",
    "apply_preset",
    "apply_overrides",
    "show_status",
    "write_config",
    "parse_args",
]


def prompt_choice(setting: dict, current_value) -> object:
    """Prompt user for a single setting. Returns new value or current."""
    key = setting["key"]
    label = setting["label"]
    description = setting["description"]
    example = setting["example"]
    stype = setting["type"]
    current_display = format_value(key, current_value)

    print(f"\n  {label} [{current_display}]")
    print(f"    What: {description}")
    print(f"    Example: {example}")

    if stype == "bool":
        raw = input(f"    on/off [{current_display}]: ").strip().lower()
        if not raw:
            return current_value
        return raw in ("on", "true", "1", "yes")
    if stype == "strict_toggle":
        raw = input(f"    on/off [{current_display}]: ").strip().lower()
        if not raw:
            return current_value
        return "strict" if raw in ("on", "true", "1", "yes") else "normal"
    if stype == "choice":
        options = ", ".join(setting["options"])
        raw = input(f"    {options} [{current_display}]: ").strip().lower()
        if not raw:
            return current_value
        if raw in setting["options"]:
            return raw
        print(f"    Invalid choice. Keeping: {current_display}")
        return current_value
    if stype == "int":
        display_hint = "0=none" if key == "max_session_minutes" else ""
        raw = input(f"    Enter number {display_hint} [{current_display}]: ").strip()
        if not raw:
            return current_value
        if raw.lower() == "none":
            return 0
        try:
            return int(raw)
        except ValueError:
            print(f"    Not a number. Keeping: {current_display}")
            return current_value
    if stype == "str":
        raw = input(f"    [{current_display}]: ").strip()
        return raw if raw else current_value
    return current_value


def interactive_wizard(project_dir: Path) -> Optional[dict]:
    """Run the full interactive wizard. Returns config or None if cancelled."""
    print("\n=== Agent Toolkit Setup ===\n")
    print("Pick a starting point (you can customize after):\n")

    for i, (name, desc) in enumerate(PRESET_DESCRIPTIONS.items(), 1):
        print(f"  {i}. {name:<10} — {desc}\n")
    print(f"  5. {'custom':<10} — Set every option yourself\n")

    raw = input("Choice [1-5]: ").strip()
    choice_map = {"1": "quick", "2": "balanced", "3": "guarded", "4": "lockdown"}

    if raw in choice_map:
        preset_name = choice_map[raw]
        config = dict(PRESETS[preset_name])
        print(f"\n--- You picked: {preset_name} ---\n")
    elif raw == "5":
        config = dict(PRESETS["balanced"])
        print("\n--- Custom mode (starting from balanced defaults) ---\n")
    else:
        print("Invalid choice.")
        return None

    print("Customize? Each setting is explained. Press Enter to keep default.\n")

    for setting in SETTINGS:
        key = setting["key"]
        current = config.get(key)
        config[key] = prompt_choice(setting, current)

    full_config = build_full_config(config)
    show_confirmation(full_config)

    confirm = input("Write to gates.json? [yes / no]: ").strip().lower()
    if confirm in ("yes", "y"):
        write_config(full_config, project_dir)
        print(f"\nWritten to {project_dir / 'gates.json'}")
        return full_config
    print("Cancelled. No changes made.")
    return None


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent Toolkit setup wizard — configure modes and settings.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  agent-toolkit-setup                    # interactive wizard\n"
            "  agent-toolkit-setup --quick             # prototype mode\n"
            "  agent-toolkit-setup --balanced          # daily dev mode\n"
            "  agent-toolkit-setup --guarded           # production mode\n"
            "  agent-toolkit-setup --lockdown          # full review mode\n"
            "  agent-toolkit-setup --tdd off           # toggle single setting\n"
            "  agent-toolkit-setup --model sonnet      # set model\n"
            "  agent-toolkit-setup --auto on --continue on  # autonomous + restart\n"
            "  agent-toolkit-setup --report-protect off  # allow agent report writes (not recommended)\n"
            "  agent-toolkit-setup --status            # show current config\n"
        ),
    )

    presets = parser.add_mutually_exclusive_group()
    presets.add_argument("--quick", action="store_true", help="Prototype mode — minimal guardrails")
    presets.add_argument("--balanced", action="store_true", help="Daily dev — TDD + routing + commit gate")
    presets.add_argument("--guarded", action="store_true", help="Production — eval on push, time-limited")
    presets.add_argument("--lockdown", action="store_true", help="Full review — strict mode, all gates")

    parser.add_argument("--tdd", choices=["on", "off"], default=None, help="TDD enforcement")
    parser.add_argument("--skill-routing", choices=["on", "off"], default=None, help="Auto skill routing")
    parser.add_argument("--enforcement", choices=["block", "warn"], default=None, help="Commit gate enforcement")
    parser.add_argument("--profile", choices=["minimal", "standard", "strict", "paranoid"], default=None)
    parser.add_argument("--strict", choices=["on", "off"], default=None, help="Strict mode")
    parser.add_argument("--auto", choices=["on", "off"], default=None, help="Auto mode (unattended)")
    parser.add_argument("--continue-mode", choices=["on", "off"], default=None, help="Auto-restart sessions")
    parser.add_argument("--time-limit", type=int, default=None, help="Session time limit in minutes (0=none)")
    parser.add_argument("--model", type=str, default=None, help="LLM model (auto/claude-opus/gpt-4o/...)")
    parser.add_argument("--eval-threshold", type=int, default=None, help="Minimum eval score (0-100)")
    parser.add_argument("--gate-protect", choices=["on", "off"], default=None, help="Block agent from writing gate files directly")
    parser.add_argument("--report-protect", choices=["on", "off"], default=None, help="Block agent from writing reports/ directly")

    parser.add_argument("--status", action="store_true", help="Show current configuration")
    parser.add_argument("--project-dir", type=str, default=".", help="Project directory")

    return parser.parse_args(argv)


def args_to_overrides(args) -> dict:
    """Convert parsed CLI args to override dict."""
    overrides = {}
    if args.tdd is not None:
        overrides["tdd"] = args.tdd == "on"
    if args.skill_routing is not None:
        overrides["skill_routing"] = args.skill_routing == "on"
    if args.enforcement is not None:
        overrides["enforcement"] = args.enforcement
    if args.profile is not None:
        overrides["profile"] = args.profile
    if args.strict is not None:
        overrides["mode"] = "strict" if args.strict == "on" else "normal"
    if args.auto is not None:
        overrides["auto"] = args.auto == "on"
    if args.continue_mode is not None:
        overrides["continue"] = args.continue_mode == "on"
    if args.time_limit is not None:
        overrides["max_session_minutes"] = args.time_limit
    if args.model is not None:
        overrides["model"] = args.model
    if args.eval_threshold is not None:
        overrides["eval_threshold"] = args.eval_threshold
    if args.gate_protect is not None:
        overrides["gate_protect"] = args.gate_protect == "on"
    if args.report_protect is not None:
        overrides["report_protect"] = args.report_protect == "on"
    return overrides


def main() -> int:
    """Entry point."""
    args = parse_args()
    project_dir = Path(args.project_dir).resolve()

    if args.status:
        show_status(project_dir)
        return 0

    for preset_name in ("quick", "balanced", "guarded", "lockdown"):
        if getattr(args, preset_name, False):
            overrides = args_to_overrides(args)
            config = apply_preset(preset_name, project_dir)
            if overrides:
                config = apply_overrides(overrides, project_dir)
            print(f"Applied preset: {preset_name}")
            show_confirmation(config)
            return 0

    overrides = args_to_overrides(args)
    if overrides:
        config = apply_overrides(overrides, project_dir)
        print("Settings updated:")
        show_confirmation(config)
        return 0

    interactive_wizard(project_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
