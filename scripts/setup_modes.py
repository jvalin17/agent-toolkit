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

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

# --- Settings definitions ---

SETTINGS = [
    {
        "key": "tdd",
        "label": "TDD enforcement",
        "description": "Reminds you to write tests before editing source files",
        "example": 'editing main.py without test_main.py -> "Write test first"',
        "type": "bool",
        "options": ["on", "off"],
    },
    {
        "key": "skill_routing",
        "label": "Skill routing",
        "description": "Auto-detects what you're doing and suggests the right workflow",
        "example": '"fix the login bug" -> routes to /debug skill',
        "type": "bool",
        "options": ["on", "off"],
    },
    {
        "key": "enforcement",
        "label": "Commit gate",
        "description": "Requires /precommit before git commit",
        "example": "block = commit fails without it, warn = reminder only",
        "type": "choice",
        "options": ["block", "warn"],
    },
    {
        "key": "profile",
        "label": "Push gate profile",
        "description": "Which skills are required before push",
        "example": "minimal = precommit only, standard = + evaluate, strict = + reviewer",
        "type": "choice",
        "options": ["minimal", "standard", "strict", "paranoid"],
    },
    {
        "key": "mode",
        "label": "Strict mode",
        "description": "Prevents agent faking. Test fixtures must cite real data sources",
        "example": "Adds drift detection and periodic integrity checks",
        "type": "strict_toggle",
        "options": ["off", "on"],
    },
    {
        "key": "eval_threshold",
        "label": "Eval threshold",
        "description": "Minimum /evaluate percentage to pass gate",
        "example": "Range: 0-100. Default: 95",
        "type": "int",
        "options": None,
    },
    {
        "key": "auto",
        "label": "Auto mode",
        "description": "Skills run without asking for your approval",
        "example": "off = you approve each step, on = agent works autonomously",
        "type": "bool",
        "options": ["off", "on"],
    },
    {
        "key": "continue",
        "label": "Continue mode",
        "description": "Sessions auto-restart when context runs out",
        "example": "Uses agent-toolkit-continue wrapper for long-running tasks",
        "type": "bool",
        "options": ["off", "on"],
    },
    {
        "key": "max_session_minutes",
        "label": "Time limit",
        "description": "Hard stop after N minutes. 0 = only stops on context exhaustion",
        "example": "Useful for preventing runaway sessions",
        "type": "int",
        "options": None,
    },
    {
        "key": "gate_protect",
        "label": "Gate protection",
        "description": "Blocks the agent from writing gate files directly (prevents bypassing /precommit)",
        "example": "on = only skill hooks can write .gates/ files, off = agent can write them",
        "type": "bool",
        "options": ["off", "on"],
    },
    {
        "key": "report_protect",
        "label": "Report protection",
        "description": "Blocks the agent from writing reports/ directly (prevents forged skill reports)",
        "example": "on = only hooks/finalize_report.py can write reports/, off = agent can write them",
        "type": "bool",
        "options": ["off", "on"],
    },
    {
        "key": "model",
        "label": "Model",
        "description": "Which LLM to use. 'auto' = whatever the tool defaults to",
        "example": "claude-opus, claude-sonnet, gpt-4o, gemini-2.5-pro, or any string",
        "type": "str",
        "options": None,
    },
]

# --- Preset definitions ---

PRESETS = {
    "quick": {
        "tdd": False,
        "skill_routing": False,
        "enforcement": "warn",
        "profile": "minimal",
        "mode": "normal",
        "eval_threshold": 95,
        "auto": False,
        "continue": False,
        "max_session_minutes": 0,
        "model": "auto",
        "gate_protect": False,
        "report_protect": True,
    },
    "balanced": {
        "tdd": True,
        "skill_routing": True,
        "enforcement": "block",
        "profile": "minimal",
        "mode": "normal",
        "eval_threshold": 95,
        "auto": False,
        "continue": False,
        "max_session_minutes": 0,
        "model": "auto",
        "gate_protect": True,
        "report_protect": True,
    },
    "guarded": {
        "tdd": True,
        "skill_routing": True,
        "enforcement": "block",
        "profile": "standard",
        "mode": "normal",
        "eval_threshold": 95,
        "auto": False,
        "continue": False,
        "max_session_minutes": 70,
        "model": "auto",
        "gate_protect": True,
        "report_protect": True,
    },
    "lockdown": {
        "tdd": True,
        "skill_routing": True,
        "enforcement": "block",
        "profile": "paranoid",
        "mode": "strict",
        "eval_threshold": 95,
        "auto": False,
        "continue": False,
        "max_session_minutes": 70,
        "model": "auto",
        "gate_protect": True,
        "report_protect": True,
    },
}

PROFILES = {
    "minimal": {
        "commit_requires": ["precommit"],
        "push_requires": [],
    },
    "standard": {
        "commit_requires": ["precommit"],
        "push_requires": ["evaluate"],
    },
    "strict": {
        "commit_requires": ["precommit", "evaluate"],
        "push_requires": ["evaluate", "reviewer"],
    },
    "paranoid": {
        "commit_requires": ["precommit", "evaluate"],
        "push_requires": ["evaluate", "reviewer", "assess"],
    },
}

PRESET_DESCRIPTIONS = {
    "quick": (
        "Minimal guardrails. No TDD checks, no skill routing.\n"
        '                 Good for: prototypes, experiments, learning\n'
        '                 Example: "I just want to code without interruptions"'
    ),
    "balanced": (
        "TDD + skill routing enabled. Commits gated.\n"
        '                 Good for: daily development, solo projects\n'
        '                 Example: "Guide me but let me work"'
    ),
    "guarded": (
        "Everything checked. Eval required on push. Time-limited.\n"
        '                 Good for: production code, team branches\n'
        '                 Example: "Check my work before it ships"'
    ),
    "lockdown": (
        "Strict mode. All reviews required. Time-limited.\n"
        '                 Good for: regulated code, compliance, audits\n'
        '                 Example: "Nothing ships without full review"'
    ),
}


# --- Config I/O ---


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
    config = {
        "gate_mode": "legacy",
        "enforcement": settings.get("enforcement", "block"),
        "profile": settings.get("profile", "minimal"),
        "mode": settings.get("mode", "normal"),
        "eval_threshold": settings.get("eval_threshold", 95),
        "max_session_minutes": settings.get("max_session_minutes", 0),
        "auto": settings.get("auto", False),
        "continue": settings.get("continue", False),
        "tdd": settings.get("tdd", True),
        "skill_routing": settings.get("skill_routing", True),
        "model": settings.get("model", "auto"),
        "gate_protect": settings.get("gate_protect", True),
        "report_protect": settings.get("report_protect", True),
        "profiles": PROFILES,
    }
    return config


# --- Preset and override application ---


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


# --- Display ---


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


# --- Interactive wizard ---


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
    elif stype == "strict_toggle":
        raw = input(f"    on/off [{current_display}]: ").strip().lower()
        if not raw:
            return current_value
        return "strict" if raw in ("on", "true", "1", "yes") else "normal"
    elif stype == "choice":
        options = ", ".join(setting["options"])
        raw = input(f"    {options} [{current_display}]: ").strip().lower()
        if not raw:
            return current_value
        if raw in setting["options"]:
            return raw
        print(f"    Invalid choice. Keeping: {current_display}")
        return current_value
    elif stype == "int":
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
    elif stype == "str":
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
        config = dict(PRESETS["balanced"])  # Start from balanced defaults
        print("\n--- Custom mode (starting from balanced defaults) ---\n")
    else:
        print("Invalid choice.")
        return None

    print("Customize? Each setting is explained. Press Enter to keep default.\n")

    for setting in SETTINGS:
        key = setting["key"]
        current = config.get(key)
        new_value = prompt_choice(setting, current)
        config[key] = new_value

    full_config = build_full_config(config)
    show_confirmation(full_config)

    confirm = input("Write to gates.json? [yes / no]: ").strip().lower()
    if confirm in ("yes", "y"):
        write_config(full_config, project_dir)
        print(f"\nWritten to {project_dir / 'gates.json'}")
        return full_config
    else:
        print("Cancelled. No changes made.")
        return None


# --- CLI ---


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

    # Presets
    presets = parser.add_mutually_exclusive_group()
    presets.add_argument("--quick", action="store_true", help="Prototype mode — minimal guardrails")
    presets.add_argument("--balanced", action="store_true", help="Daily dev — TDD + routing + commit gate")
    presets.add_argument("--guarded", action="store_true", help="Production — eval on push, time-limited")
    presets.add_argument("--lockdown", action="store_true", help="Full review — strict mode, all gates")

    # Individual settings
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

    # Meta
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

    # Status mode
    if args.status:
        show_status(project_dir)
        return 0

    # Preset mode
    for preset_name in ("quick", "balanced", "guarded", "lockdown"):
        if getattr(args, preset_name, False):
            overrides = args_to_overrides(args)
            config = apply_preset(preset_name, project_dir)
            if overrides:
                config = apply_overrides(overrides, project_dir)
            print(f"Applied preset: {preset_name}")
            show_confirmation(config)
            return 0

    # Individual overrides (no preset)
    overrides = args_to_overrides(args)
    if overrides:
        config = apply_overrides(overrides, project_dir)
        print("Settings updated:")
        show_confirmation(config)
        return 0

    # No flags — interactive wizard
    interactive_wizard(project_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
