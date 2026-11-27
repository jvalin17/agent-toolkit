#!/usr/bin/env python3
"""Developer mode — the toolkit's own hooks step aside while the toolkit is being changed.

On only when both hold:

1. the host was launched with ``AGENT_TOOLKIT_DEV=1``;
2. the project being worked in is the toolkit this hook was loaded from: the
   git top level of the working directory is the parent of the running hook's
   ``hooks/`` folder. Where the host names the folder it was launched in
   (``CLAUDE_PROJECT_DIR``), that folder must be in the toolkit as well.

In any other project the variable does nothing. A git worktree of the toolkit
counts as another project: its top level is not the folder the hooks run from.

THE ONE EXCEPTION. Everywhere else in the toolkit an environment variable may
only strengthen enforcement, never weaken it (``mode_resolver``,
``gate_hook``). This variable switches every hook off. It is allowed because
it is tied to the toolkit's own repository and cannot reach a user's project.
Do not add a second exception.

Every registered hook asks this module first, before any other import, so a
half-edited sibling module cannot crash a hook. For that reason this file uses
the standard library only and must never import another toolkit module.

Requirement: requirements/developer-mode.md.
"""

import json
import os
import sys

VARIABLE = "AGENT_TOOLKIT_DEV"
ON_VALUE = "1"
LAUNCH_DIR_VARIABLE = "CLAUDE_PROJECT_DIR"  # set by the host for its hooks; absent on other hosts
NOTICE = (
    "AGENT TOOLKIT: developer mode is on (AGENT_TOOLKIT_DEV=1 in the toolkit's own repository). "
    "The toolkit is not applied in this session: no hook checks, blocks or records anything. "
    "Run /precommit by hand before committing."
)


def _git_top_level(start):
    """The nearest folder at or above ``start`` that holds a ``.git`` entry, or "" when none does."""
    folder = os.path.realpath(start)
    while True:
        if os.path.exists(os.path.join(folder, ".git")):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            return ""
        folder = parent


def is_on(hook_file, environ=None, cwd=None):
    """True when developer mode applies to the hook at ``hook_file``."""
    environ = os.environ if environ is None else environ
    if environ.get(VARIABLE) != ON_VALUE:
        return False
    toolkit_root = os.path.dirname(os.path.dirname(os.path.realpath(hook_file)))
    if _git_top_level(os.getcwd() if cwd is None else str(cwd)) != toolkit_root:
        return False
    # Where the host says which folder it was launched in, that must be the
    # toolkit too: a session started in a user's project keeps its hooks even
    # if the working directory later moves into the toolkit.
    launch_dir = environ.get(LAUNCH_DIR_VARIABLE)
    return not launch_dir or _git_top_level(launch_dir) == toolkit_root


def exit_if_on(hook_file):
    """For a hook, as its first statement: leave at once with success in developer mode."""
    if is_on(hook_file):
        sys.exit(0)


def announce_and_exit_if_on(hook_file):
    """For the session start hook: say that developer mode is on, then leave with success."""
    if not is_on(hook_file):
        return
    print(json.dumps({
        "systemMessage": NOTICE,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": NOTICE},
    }))
    sys.exit(0)


if __name__ == "__main__":
    # For shell hooks: ``dev_mode.py <hook file>`` exits 0 when developer mode is on, 1 when not.
    sys.exit(0 if len(sys.argv) > 1 and is_on(sys.argv[1]) else 1)
