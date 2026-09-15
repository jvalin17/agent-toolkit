"""Preset and setting definitions for setup_modes.

Modes: minimal, tdd, planned, guarded, default, standard, safe.
See hooks/mode_resolver.py for the canonical mode definitions.
"""

SETTINGS = [
    {
        "key": "mode",
        "label": "Enforcement mode",
        "description": "Controls which checks are enforced (TDD, plan ordering, precommit, reviewer)",
        "example": "default = TDD + precommit, safe = all checks + reviewer on push",
        "type": "choice",
        "options": ["minimal", "tdd", "planned", "guarded", "default", "standard", "safe"],
    },
    {
        "key": "skill_routing",
        "label": "Skill routing",
        "description": "Auto-detects what you're doing and suggests the right workflow",
        "example": '"fix the login bug" -> routes to /debug_tool skill',
        "type": "bool",
        "options": ["on", "off"],
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
        "options": ["on", "off"],
    },
    {
        "key": "continue",
        "label": "Continue mode",
        "description": "Sessions auto-restart when context runs out",
        "example": "Uses agent-toolkit-continue wrapper for long-running tasks",
        "type": "bool",
        "options": ["on", "off"],
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
        "example": "on = only hooks/finalize_report.py can write .gates/ (default)",
        "type": "bool",
        "options": ["off", "on"],
    },
    {
        "key": "report_protect",
        "label": "Report protection",
        "description": "Blocks the agent from writing reports/ directly (prevents forged skill reports)",
        "example": "on = only hooks/finalize_report.py can write reports/ (default)",
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

PRESETS = {
    "quick": {
        "mode": "minimal",
        "skill_routing": False,
        "eval_threshold": 95,
        "auto": False,
        "continue": False,
        "max_session_minutes": 0,
        "model": "auto",
        "gate_protect": False,
        "report_protect": True,
    },
    "balanced": {
        "mode": "default",
        "skill_routing": True,
        "eval_threshold": 95,
        "auto": False,
        "continue": False,
        "max_session_minutes": 0,
        "model": "auto",
        "gate_protect": True,
        "report_protect": True,
    },
    "guarded": {
        "mode": "standard",
        "skill_routing": True,
        "eval_threshold": 95,
        "auto": False,
        "continue": False,
        "max_session_minutes": 70,
        "model": "auto",
        "gate_protect": True,
        "report_protect": True,
    },
    "lockdown": {
        "mode": "safe",
        "skill_routing": True,
        "eval_threshold": 95,
        "auto": False,
        "continue": False,
        "max_session_minutes": 70,
        "model": "auto",
        "gate_protect": True,
        "report_protect": True,
    },
}

PRESET_DESCRIPTIONS = {
    "quick": (
        "No enforcement — for local experiments only.\n"
        "                 Good for: learning the toolkit layout\n"
        '                 Prefer: balanced or guarded for real work'
    ),
    "balanced": (
        "TDD + precommit enforced. Commits gated.\n"
        '                 Good for: daily development, solo projects\n'
        '                 Example: "Guide me but let me work"'
    ),
    "guarded": (
        "TDD + plan + precommit enforced. Time-limited.\n"
        '                 Good for: production code, team branches\n'
        '                 Example: "Check my work before it ships"'
    ),
    "lockdown": (
        "All checks + reviewer on push. Time-limited.\n"
        '                 Good for: regulated code, compliance, audits\n'
        '                 Example: "Nothing ships without full review"'
    ),
}
