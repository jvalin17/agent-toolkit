"""Mode resolver — single source of truth for toolkit enforcement modes.

Replaces the old profile/tdd/tdd_mode/enforcement/mode system with
a single "mode" field in gates.json. Seven modes:

  minimal   — no checks
  tdd       — TDD enforcement only
  planned   — test plan ordering only
  guarded   — precommit gate only
  default   — TDD + precommit (the default)
  standard  — TDD + plan + precommit
  safe      — TDD + plan + precommit + reviewer

Usage:
    from mode_resolver import resolve_mode, resolve_mode_from_config

    mode = resolve_mode("default")
    mode.tdd          # True
    mode.plan         # False
    mode.precommit    # True
    mode.reviewer     # False
    mode.commit_requires  # ["precommit"]
    mode.push_requires    # []
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Mode:
    """Resolved enforcement mode with boolean flags and skill requirements."""
    name: str
    tdd: bool
    plan: bool
    precommit: bool
    reviewer: bool

    @property
    def commit_requires(self) -> List[str]:
        skills = []
        if self.precommit:
            skills.append("precommit")
        return skills

    @property
    def push_requires(self) -> List[str]:
        skills = []
        if self.reviewer:
            skills.append("reviewer")
        return skills


MODES = {
    "minimal":  Mode(name="minimal",  tdd=False, plan=False, precommit=False, reviewer=False),
    "tdd":      Mode(name="tdd",      tdd=True,  plan=False, precommit=False, reviewer=False),
    "planned":  Mode(name="planned",  tdd=False, plan=True,  precommit=False, reviewer=False),
    "guarded":  Mode(name="guarded",  tdd=False, plan=False, precommit=True,  reviewer=False),
    "default":  Mode(name="default",  tdd=True,  plan=False, precommit=True,  reviewer=False),
    "standard": Mode(name="standard", tdd=True,  plan=True,  precommit=True,  reviewer=False),
    "safe":     Mode(name="safe",     tdd=True,  plan=True,  precommit=True,  reviewer=True),
}

DEFAULT_MODE = "default"


def resolve_mode(name: str) -> Mode:
    """Resolve a mode name to its Mode object. Falls back to default."""
    return MODES.get(name, MODES[DEFAULT_MODE])


def resolve_mode_from_config(config: dict) -> Mode:
    """Resolve mode from gates.json config, with env var override."""
    env_mode = os.environ.get("AGENT_TOOLKIT_MODE")
    if env_mode:
        return resolve_mode(env_mode)
    return resolve_mode(config.get("mode", DEFAULT_MODE))
