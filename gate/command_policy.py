"""Allowlist for repo-supplied commands (gates.json test_command / lint_command).

A cloned repository controls its gates.json. Without this check, cloning a
hostile repo and running /precommit, /evaluate or the CI gate would execute
whatever that file says, as the user. Only known test/lint runners are
accepted, with no shell metacharacters and no "run arbitrary code" sub-modes.
A runner is invoked by bare name (resolved on PATH) or from a project-local
tool directory (a virtualenv's bin/ or Scripts/, or node_modules/.bin/), which
is how most projects spell their test command. Any other path is refused.
"""

from __future__ import annotations

import re
from typing import Sequence, Tuple

# Runner → sub-modes that are refused even for a trusted runner.
TRUSTED_RUNNERS: dict[str, frozenset[str]] = {
    "python": frozenset({"-c", "-"}),
    "python3": frozenset({"-c", "-"}),
    "pytest": frozenset({"-p"}),
    "ruff": frozenset(),
    "flake8": frozenset(),
    "mypy": frozenset(),
    "pylint": frozenset(),
    "black": frozenset(),
    "npm": frozenset({"exec", "x", "run-script", "install", "ci", "publish"}),
    "npx": frozenset(),
    "yarn": frozenset({"exec", "dlx", "install", "add"}),
    "pnpm": frozenset({"exec", "dlx", "install", "add"}),
    "node": frozenset({"-e", "--eval", "-p", "--print"}),
    "jest": frozenset(),
    "vitest": frozenset(),
    "eslint": frozenset(),
    "tsc": frozenset(),
    "go": frozenset({"run", "generate", "install", "get"}),
    "cargo": frozenset({"run", "install"}),
    "make": frozenset(),
    "gradle": frozenset(),
    "./gradlew": frozenset(),
    "mvn": frozenset({"exec:java", "exec:exec"}),
    "dotnet": frozenset({"run", "tool"}),
    "bundle": frozenset({"exec"}),
    "rspec": frozenset(),
    "rubocop": frozenset(),
    "phpunit": frozenset(),
    "composer": frozenset({"run", "run-script", "exec"}),
    "mix": frozenset({"run"}),
    "swift": frozenset({"run"}),
    "xcodebuild": frozenset(),
    "true": frozenset(),  # explicit no-op, used by CI fixtures and demos
}

# python -m <module>: only these modules run.
TRUSTED_PYTHON_MODULES = frozenset({"pytest", "unittest", "compileall", "ruff", "flake8", "mypy", "pylint", "black"})
# npm/yarn/pnpm scripts that are acceptable targets.
TRUSTED_SCRIPT_TARGETS = frozenset({"test", "lint", "typecheck", "check", "test:unit", "test:ci", "lint:ci"})
# make targets considered safe.
TRUSTED_MAKE_TARGETS = frozenset({"test", "lint", "check", "typecheck", "unit", "ci"})

SHELL_META = re.compile(r"[;&|`$<>(){}\\]|\n")
# argv[0] may be a path, so backslashes are allowed there (Windows venvs); no other shell characters.
RUNNER_TOKEN = re.compile(r"^[A-Za-z0-9_.\-/\\]+$")

# Project-local tool directories, relative to the project root, whose binaries
# are treated as the runner of the same name: `.venv/bin/python -m pytest`,
# `node_modules/.bin/jest`. Nothing outside the project root is accepted.
PROJECT_TOOL_DIR = re.compile(
    r"^(?:\./)?(?:(?:\.?venv|\.?env)/(?:bin|Scripts)|node_modules/\.bin)/"
    r"(?P<name>[A-Za-z0-9_.\-]+?)(?:\.exe|\.cmd)?$"
)
PYTHON_VERSIONED = re.compile(r"^python3(?:\.\d+)?$")
PROJECT_LOCAL_HINT = "project-local .venv/bin/<runner> or node_modules/.bin/<runner> is also accepted"


def _runner_name(token: str) -> str | None:
    """Bare runner name for argv[0], or None when it is a path we do not trust."""
    if token == "./gradlew":
        return token
    match = PROJECT_TOOL_DIR.match(token.replace("\\", "/"))
    if match:
        name = match.group("name")
        return "python3" if PYTHON_VERSIONED.match(name) else name
    if "/" in token or "\\" in token:
        return None  # arbitrary paths are not trusted; runners resolve on PATH
    return token


def check_command(argv: Sequence[str]) -> Tuple[bool, str]:
    """(ok, reason). Reason is empty when ok."""
    if not argv:
        return False, "empty command"
    if not RUNNER_TOKEN.match(argv[0]):
        return False, f"shell metacharacter in runner {argv[0]!r}"
    for tok in argv[1:]:
        if SHELL_META.search(tok):
            return False, f"shell metacharacter in argument {tok!r}"

    runner = _runner_name(argv[0])
    if runner is None or runner not in TRUSTED_RUNNERS:
        return False, (
            f"runner {argv[0]!r} is not allowlisted "
            f"(trusted: {', '.join(sorted(TRUSTED_RUNNERS))}; {PROJECT_LOCAL_HINT})"
        )

    forbidden = TRUSTED_RUNNERS[runner]
    rest = list(argv[1:])
    hit = next((t for t in rest if t in forbidden), None)
    if hit is not None:
        return False, f"{runner} {hit} runs arbitrary code"

    if runner in ("python", "python3"):
        if not rest or rest[0] != "-m":
            return False, "python is only trusted as `python -m <test or lint module>`"
        module = rest[1] if len(rest) > 1 else ""
        if module not in TRUSTED_PYTHON_MODULES:
            return False, f"python -m {module!r} is not a trusted test/lint module"
    elif runner in ("npm", "yarn", "pnpm"):
        sub = next((t for t in rest if not t.startswith("-")), "")
        target = sub
        if sub in ("run", "run-script"):
            target = next((t for t in rest[rest.index(sub) + 1:] if not t.startswith("-")), "")
        if target not in TRUSTED_SCRIPT_TARGETS:
            return False, f"{runner} script {target!r} is not a trusted test/lint target"
    elif runner == "make":
        targets = [t for t in rest if not t.startswith("-") and "=" not in t]
        if any(t not in TRUSTED_MAKE_TARGETS for t in targets):
            return False, f"make target(s) {targets} are not trusted test/lint targets"
    return True, ""
