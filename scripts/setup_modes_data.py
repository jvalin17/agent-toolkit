"""Preset and setting definitions for setup_modes."""

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
        "key": "tdd_mode",
        "label": "TDD mode",
        "description": "Remind (default) or block source edits until tests exist",
        "example": "strict = block edits without tests; remind = advisory only",
        "type": "choice",
        "options": ["remind", "strict"],
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
        "tdd": False,
        "tdd_mode": "remind",
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
        "tdd_mode": "remind",
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
        "tdd_mode": "remind",
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
        "tdd_mode": "remind",
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
        "Local experiments only — not for production.\n"
        "                 Disables structural gate protection and uses advisory enforcement.\n"
        '                 Good for: learning the toolkit layout\n'
        '                 Prefer: balanced or guarded for real work'
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
