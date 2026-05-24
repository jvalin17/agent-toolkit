#!/usr/bin/env python3
"""route_to_skill.py — Detects user intent and injects skill routing context.

Runs as UserPromptSubmit hook. Reads the user's prompt, detects what
they're trying to do, and injects context telling Claude WHICH skill
to use and HOW to follow it.

Replaces route-to-skill.sh.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

# Ensure sibling modules are importable regardless of CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate_hook import get_config_value, load_gate_config

# Intent patterns — order matters (first match wins).
# Each entry: (compiled_regex, skill_context_builder)

INTENT_PATTERNS = [
    # Bug fix / something broken — scoped to avoid "fix the design"
    (
        re.compile(
            r"fix.*(bug|error|crash|issue|problem|fail|broken)"
            r"|bug.*(fix|in|with|on)"
            r"|broken|crash"
            r"|not working|doesn.t work"
            r"|blank page|0 results|silent fail"
            r"|throwing.*error|getting.*error",
            re.IGNORECASE,
        ),
        "debug",
    ),
    # Deploy / setup — before build so "set up env" matches setup not build
    (
        re.compile(
            r"deploy"
            r"|setup.*(project|app|env)"
            r"|set up.*(project|app|env)"
            r"|install.*(script|dep)"
            r"|docker|dockerfile|makefile"
            r"|ci.*(cd|pipeline)",
            re.IGNORECASE,
        ),
        "setup",
    ),
    # Build / implement / add feature
    (
        re.compile(
            r"build|implement|create"
            r"|add.*(feature|endpoint|page|component|module)"
            r"|new.*(feature|app|project)"
            r"|set up|scaffold"
            r"|make.*(a|an|the).*(app|service|api|tool)",
            re.IGNORECASE,
        ),
        "build",
    ),
    # Refactor
    (
        re.compile(
            r"refactor|clean up|restructure|reorganize"
            r"|simplify.*(code|logic|module)",
            re.IGNORECASE,
        ),
        "refactor",
    ),
    # Understand / explore codebase
    (
        re.compile(
            r"understand"
            r"|explore.*(code|repo|project)"
            r"|what does.*(this|the).*(do|code)"
            r"|how does.*(this|the).*(work|code)"
            r"|onboard|walk me through",
            re.IGNORECASE,
        ),
        "explore",
    ),
    # Review / check quality
    (
        re.compile(
            r"review.*(code|pr|change|pull)"
            r"|check.*(quality|code)"
            r"|audit|how good|grade|score|evaluate",
            re.IGNORECASE,
        ),
        "review",
    ),
    # Requirements / planning
    (
        re.compile(
            r"gather.*(require|spec)"
            r"|plan.*(feature|project|app)"
            r"|scope"
            r"|what should.*(we|i) build"
            r"|feature list|user stor",
            re.IGNORECASE,
        ),
        "requirements",
    ),
    # Architecture / design
    (
        re.compile(
            r"architect"
            r"|design.*(system|api|database|schema)"
            r"|tech stack"
            r"|which.*(database|framework|pattern)"
            r"|choose.*(between|stack)",
            re.IGNORECASE,
        ),
        "architecture",
    ),
]

SKILL_CONTEXTS = {
    "debug": (
        "SKILL ROUTING: This looks like a bug fix. You MUST follow the /debug workflow:\n"
        "1. Read skills/debug/SKILL.md — follow it strictly\n"
        "2. Hypothesis-driven: form hypotheses, test them, eliminate\n"
        "3. Write a FAILING test that reproduces the bug BEFORE fixing\n"
        "4. Fix the code to make the test pass\n"
        "5. Run /precommit before committing\n"
        "Do NOT just edit the file and say 'fixed'. Follow the skill file step by step."
    ),
    "build": (
        "SKILL ROUTING: This is a build/implement task. You MUST follow the /implementation workflow:\n"
        "1. Read skills/implementation/SKILL.md — follow it strictly\n"
        "2. If no requirements exist: run /requirements first (ask Q1 + Q4, draft early)\n"
        "3. If no architecture exists: run /architecture first (design with evidence)\n"
        "4. Create a code change plan BEFORE writing any code\n"
        "5. Build slab-by-slab with TDD — test first, then implementation\n"
        "6. Run /precommit before committing\n"
        "Do NOT just start writing code. Read the skill file and follow the flow."
    ),
    "refactor": (
        "SKILL ROUTING: This is a refactor task. You MUST follow /implementation in refactor mode:\n"
        "1. Read skills/implementation/SKILL.md — follow refactor mode\n"
        "2. Ensure all tests pass BEFORE refactoring\n"
        "3. Refactor in small steps — tests must pass after each step\n"
        "4. Run /precommit before committing\n"
        "Do NOT refactor without confirming tests pass first."
    ),
    "explore": (
        "SKILL ROUTING: This is a codebase exploration. Use /explore:\n"
        "1. Read skills/explore/SKILL.md — follow the 4-phase analysis\n"
        "2. Recon → Architecture → Conventions → Issues\n"
        "3. Write findings to project-state.md"
    ),
    "review": (
        "SKILL ROUTING: This is a quality check. Use the appropriate skill:\n"
        "- Code review → /reviewer (read skills/reviewer/SKILL.md)\n"
        "- Quality score → /evaluate (read skills/evaluate/SKILL.md)\n"
        "- Architecture fitness → /assess (read skills/assess/SKILL.md)\n"
        "Read the skill file and follow it strictly."
    ),
    "setup": (
        "SKILL ROUTING: This is a setup/deploy task. Use /setup:\n"
        "1. Read skills/setup/SKILL.md — follow it strictly\n"
        "2. Generate install scripts, Docker config, README from code analysis"
    ),
    "requirements": (
        "SKILL ROUTING: This is requirements gathering. Use /requirements:\n"
        "1. Read skills/requirements/SKILL.md — follow it strictly\n"
        "2. Ask Q1 (what?) + Q4 (how do you do this today?) — draft early\n"
        "3. Go deeper on demand, don't force all questions upfront\n"
        "4. Keep responses focused — ask ONE question at a time, don't dump information"
    ),
    "architecture": (
        "SKILL ROUTING: This is architecture/design. Use /architecture:\n"
        "1. Read skills/architecture/SKILL.md — follow it strictly\n"
        "2. Present 2-3 options with trade-offs, user decides\n"
        "3. Log decisions with evidence in project-state.md"
    ),
}


def detect_intent(prompt: str) -> Optional[str]:
    """Match prompt against intent patterns. Returns skill key or None."""
    for pattern, skill_key in INTENT_PATTERNS:
        if pattern.search(prompt):
            return skill_key
    return None


def make_hook_response(message: str) -> str:
    """Build Claude Code UserPromptSubmit hook JSON response."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": message,
            }
        }
    )


def run_route_to_skill(
    stdin_input: str,
    project_dir: Path,
) -> Tuple[int, str]:
    """Detect intent and inject skill routing. Returns (exit_code, output)."""
    config = load_gate_config(project_dir)
    if not get_config_value(config, "skill_routing", True):
        return 0, ""

    try:
        hook_input = json.loads(stdin_input)
        prompt = hook_input.get("prompt", "")
    except (json.JSONDecodeError, TypeError, AttributeError):
        return 0, ""

    if not prompt:
        return 0, ""

    # If user is already invoking a skill, don't interfere
    if prompt.lstrip().startswith("/"):
        return 0, ""

    intent = detect_intent(prompt)
    if intent is None:
        return 0, ""

    context = SKILL_CONTEXTS[intent]
    return 0, make_hook_response(context)


def main() -> int:
    """Entry point — reads hook input from stdin."""
    stdin_input = sys.stdin.read()
    project_dir = Path.cwd()
    exit_code, output = run_route_to_skill(stdin_input, project_dir)
    if output:
        print(output)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
