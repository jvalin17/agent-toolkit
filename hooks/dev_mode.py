#!/usr/bin/env python3
"""Developer mode — the toolkit's own hooks step aside while the toolkit is being changed.

On only when both hold:

1. the host was launched with ``AGENT_TOOLKIT_DEV=1``;
2. the project being worked in is the toolkit's own repository. Where the
   host names the folder it was launched in (``CLAUDE_PROJECT_DIR``), that
   folder must be in the toolkit's repository as well.

Which repository is the toolkit's own depends on where the running hook is:

- a hook loaded from a git checkout: the repository holding its ``hooks/``
  folder, meaning the main checkout and every linked worktree of it;
- a separately installed copy (the plugin copy, in no checkout of its own):
  the repository named in ``~/.agent-toolkit/dev-repo``. Only the session
  start hook of a checkout writes that record, and only when developer mode
  is on for it. A copy never writes it, and a checkout never reads it.

In any other project the variable does nothing. A folder that merely points at
the toolkit (a hand-written ``.git`` file, a submodule, a nested repository)
is another project: a linked worktree counts only when the repository names
it back.

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
import stat
import sys

VARIABLE = "AGENT_TOOLKIT_DEV"
ON_VALUE = "1"
LAUNCH_DIR_VARIABLE = "CLAUDE_PROJECT_DIR"  # set by the host for its hooks; absent on other hosts
RECORD_FOLDER = ".agent-toolkit"  # under the home folder; every copy of the hooks protects it from the agent
RECORD_NAME = "dev-repo"
RECORD_FOLDER_MODE = 0o700  # the owner only, like the signing key beside it
RECORD_FILE_MODE = 0o600
WORKTREE_POINTER = "gitdir:"
NOTICE = (
    "AGENT TOOLKIT: developer mode is on (AGENT_TOOLKIT_DEV=1 in the toolkit's own repository). "
    "The toolkit is not applied in this session: no hook checks or blocks anything, "
    "and nothing is recorded in the project. "
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


def _first_line(path):
    """The first line of the file at ``path`` without surrounding space, or "" when it cannot be read."""
    try:
        if not os.path.isfile(path):
            return ""  # a pipe or a device put there would keep every hook waiting
        with open(path, encoding="utf-8") as handle:
            return handle.readline().strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _pointer(path, base, prefix=""):
    """The folder git names on the first line of the file at ``path``, or "" when it names none."""
    line = _first_line(path)
    target = line[len(prefix):].strip() if line.startswith(prefix) else ""
    return os.path.realpath(os.path.join(base, target)) if target else ""


def _main_checkout(top_level):
    """The main checkout of the repository whose working tree is ``top_level``.

    That is ``top_level`` itself unless it is a linked worktree that git's own
    records confirm in both directions: its ``.git`` file names an entry under
    the repository's ``.git/worktrees/``, and that entry names it back.
    """
    dot_git = os.path.join(top_level, ".git")
    # A link is never followed: one aimed at a real worktree's ``.git`` file
    # would borrow that worktree's records for a folder that is not it.
    if os.path.islink(dot_git) or os.path.isdir(dot_git):
        return top_level
    entry = _pointer(dot_git, top_level, WORKTREE_POINTER)
    if not entry:
        return top_level
    git_folder = _pointer(os.path.join(entry, "commondir"), entry)
    named_back = _pointer(os.path.join(entry, "gitdir"), entry) == dot_git
    is_worktree_entry = bool(git_folder) and os.path.dirname(entry) == os.path.join(git_folder, "worktrees")
    if not (named_back and is_worktree_entry and os.path.basename(git_folder) == ".git"):
        return top_level
    return os.path.dirname(git_folder)


def _repository(folder):
    """The main checkout of the repository that ``folder`` is in, or "" when it is in none."""
    top_level = _git_top_level(folder)
    return _main_checkout(top_level) if top_level else ""


def _record_file(environ):
    home = environ.get("HOME") or os.path.expanduser("~")
    return os.path.join(home, RECORD_FOLDER, RECORD_NAME)


def _recorded_toolkit(environ):
    """The toolkit checkout named in the record, or "" when it names none."""
    named = _first_line(_record_file(environ))
    # A relative entry would mean "wherever the hook happens to run": only the
    # full path that ``_record_toolkit`` writes names a folder.
    if not os.path.isabs(named):
        return ""
    recorded = os.path.realpath(named)
    dot_git = os.path.join(recorded, ".git")
    is_main_checkout = os.path.isdir(dot_git) and not os.path.islink(dot_git)
    is_toolkit = os.path.isfile(os.path.join(recorded, "hooks", os.path.basename(__file__)))
    return recorded if is_main_checkout and is_toolkit else ""


def _loaded_from_checkout(hook_file):
    """The main checkout the hook was loaded from, or "" for a separately installed copy."""
    toolkit_root = os.path.dirname(os.path.dirname(os.path.realpath(hook_file)))
    return _main_checkout(toolkit_root) if _git_top_level(toolkit_root) == toolkit_root else ""


def is_on(hook_file, environ=None, cwd=None):
    """True when developer mode applies to the hook at ``hook_file``."""
    environ = os.environ if environ is None else environ
    if environ.get(VARIABLE) != ON_VALUE:
        return False
    toolkit = _loaded_from_checkout(hook_file) or _recorded_toolkit(environ)
    if not toolkit or _repository(os.getcwd() if cwd is None else str(cwd)) != toolkit:
        return False
    # Where the host says which folder it was launched in, that must be the
    # toolkit too: a session started in a user's project keeps its hooks even
    # if the working directory later moves into the toolkit.
    launch_dir = environ.get(LAUNCH_DIR_VARIABLE)
    return not launch_dir or _repository(launch_dir) == toolkit


def _owner_only(path, mode, directory):
    """Take away what group and others may do with ``path``, and say whether it is ours to use.

    True: a folder (or file) of the kind asked for, owned by this account, now closed to others.
    False: a link, another kind of entry, or someone else's. None: nothing is there, or it
    cannot be opened to tell (the write that follows then reports why).
    The entry is opened without following a link and changed through that same
    handle, so what was checked is what is changed.
    """
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | (os.O_DIRECTORY if directory else 0)
    try:
        handle = os.open(path, flags)
    except (FileNotFoundError, PermissionError):
        return None
    except OSError:
        return False
    try:
        found = os.fstat(handle)
        right_kind = stat.S_ISDIR(found.st_mode) if directory else stat.S_ISREG(found.st_mode)
        if not right_kind or found.st_uid != os.getuid():
            return False
        if stat.S_IMODE(found.st_mode) & ~mode:
            os.fchmod(handle, mode)
        return True
    except OSError:
        return False
    finally:
        os.close(handle)


def _remove(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _record_toolkit(hook_file, environ=None):
    """Note where the toolkit's checkout is, so an installed copy can step aside there too.

    Only a hook loaded from a checkout does this: an installed copy does not
    know where the toolkit is and must never name a project itself.
    """
    environ = os.environ if environ is None else environ
    toolkit = _loaded_from_checkout(hook_file)
    record = _record_file(environ)
    if not toolkit:
        return
    folder = os.path.dirname(record)
    # Every start, not only when the record changes: a folder made earlier, by
    # anything, may be open to other accounts.
    folder_is_ours = _owner_only(folder, RECORD_FOLDER_MODE, directory=True)
    if folder_is_ours:
        _owner_only(record, RECORD_FILE_MODE, directory=False)
    if _recorded_toolkit(environ) == toolkit:
        return
    if folder_is_ours is False and not os.path.islink(folder):
        # Someone else's folder, or not a folder: whoever owns it could rewrite the record.
        sys.stderr.write(
            f"developer mode: {folder} is not a folder of this account, so where the toolkit is was not "
            "recorded and an installed copy keeps its hooks on\n"
        )
        return
    draft = f"{record}.{os.getpid()}"
    draft_is_ours = False
    try:
        os.makedirs(folder, mode=RECORD_FOLDER_MODE, exist_ok=True)
        # Created new and never through a link: whatever already sits at the draft name stops the write.
        descriptor = os.open(draft, os.O_WRONLY | os.O_CREAT | os.O_EXCL, RECORD_FILE_MODE)
        draft_is_ours = True
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(toolkit + "\n")
        os.replace(draft, record)
    except (OSError, ValueError) as exc:  # ValueError: a path that cannot be written as text
        if draft_is_ours:
            _remove(draft)
        sys.stderr.write(
            f"developer mode: could not record where the toolkit is, so an installed copy keeps its hooks on: {exc!r}\n"
        )


def exit_if_on(hook_file):
    """For a hook, as its first statement: leave at once with success in developer mode."""
    if is_on(hook_file):
        sys.exit(0)


def announce_and_exit_if_on(hook_file):
    """For the session start hook: say that developer mode is on, then leave with success."""
    if not is_on(hook_file):
        return
    _record_toolkit(hook_file)
    print(json.dumps({
        "systemMessage": NOTICE,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": NOTICE},
    }))
    sys.exit(0)


if __name__ == "__main__":
    # For shell hooks: ``dev_mode.py <hook file>`` exits 0 when developer mode is on, 1 when not.
    sys.exit(0 if len(sys.argv) > 1 and is_on(sys.argv[1]) else 1)
