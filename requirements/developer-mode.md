# Requirements: developer-mode

Decided by the user 2026-11-27.

## Problem Statement

The toolkit's hooks run live from this repo's `hooks/` folder. While the toolkit itself is being changed, its own hooks police the work: a half-edited helper can crash every hook, and the gates built for user projects block edits to the gates themselves.

In the user's words: "we should have a developer mode where we don't apply the toolkit." On the switch: "launch variable and toolkit repo only." And: "just fix the dev mode where agent toolkit's own hooks don't block our way."

## Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| 1 | Developer mode is on only when the host was launched with `AGENT_TOOLKIT_DEV=1` | must |
| 2 | Developer mode is on only when the project being worked in is the toolkit's own repository. For hooks loaded from a checkout, that is the repository holding the running hook's `hooks/` folder: its main checkout or any linked git worktree of it (2a). For a separately installed copy, that is the repository recorded under requirement 8. In any other project the variable does nothing | must |
| 2a | A linked git worktree counts as its repository only when git's own records agree in both directions: the worktree's `.git` file names an entry under the repository's `.git/worktrees/`, and that entry names the worktree back. A folder that merely points at the toolkit (a hand-written `.git` file, a submodule, a nested repository) is another project | must |
| 8 | A separately installed copy of the toolkit's hooks (for example the plugin copy, which is in no git checkout of its own) steps aside in the toolkit's own repository too. It learns where that repository is from a record, `~/.agent-toolkit/dev-repo`, which only the session start hook loaded from the toolkit's own checkout writes, and only when developer mode is on for it. With no record, or a record naming a folder that is not a toolkit checkout, an installed copy keeps its hooks on | must |
| 3 | When on, every registered hook exits at once with success and applies nothing, including `check_doc_write.sh` | must |
| 4 | The early exit comes before any other import of the hook, so a half-edited sibling module cannot crash a hook. The check lives in a small module that uses the standard library only | must |
| 5 | Session start prints that developer mode is on and the toolkit is not applied | must |
| 6 | `/precommit` still runs by hand | must |
| 7 | No gate integrity starting record is written in developer mode | must |

## Boundaries

- This is the one exception to "an environment variable may only strengthen" (`mode_resolver`, `gate_hook`). The code says so where the check lives.
- Narrower than requirement 2, never wider (added after review, 2026-11-27): where the host names the folder it was launched in (`CLAUDE_PROJECT_DIR`), that folder must be in the toolkit too, so a session started in a user's project keeps its hooks if the working directory later moves into the toolkit.
- Changed by the user 2026-11-27 ("fix developer mode correctly"): a git worktree of the toolkit first counted as another project, and an installed copy was not covered. Unfinished work is done in worktrees and the plugin copy kept blocking it, so requirements 2a and 8 were added.
- The record of requirement 8 is the only thing developer mode writes. It sits in `~/.agent-toolkit/`, which every copy of the hooks protects from the agent in a policed session, and it never switches anything on by itself: an installed copy still needs the launch variable in its own process, and still compares the working directory and the launch folder with the recorded repository.
- A checkout's own hooks never read the record: they go by where they were loaded from, as before.
- Added after the security review of 2026-11-27. A `.git` entry that is a link is never followed, in a working folder or in the recorded folder: a link aimed at a real worktree's `.git` file would borrow that worktree's records. The record is written through a draft file that is created new, never through a link already at that name. `path_protection` refuses a shell command or edit that names the `~/.agent-toolkit` folder itself, not only paths below it (`cd ~/.agent-toolkit && … > dev-repo` was allowed before).
- Stated limit: the record is trusted as far as `~/.agent-toolkit/` is protected, which is the same protection the signing key has. A deliberately disguised shell command that gets past `path_protection` (section K of `pilot-assist.md` lists the kind) could write a record naming another project; an installed copy would then step aside there, if that session was also launched with the variable. Where the toolkit's own checkout is registered as well, its hooks do not read the record and stay on.
- Stated limit: on a host that does not name its launch folder, the launch-folder check does not exist, as before this change.
- Stated limit: an installed copy that sits at the top of a git checkout of its own (a plugin served straight from a clone) counts as a checkout, does not read the record, and keeps its hooks on in the toolkit's repository.
- A fault in the check itself (a broken or missing `hooks/dev_mode.py`) means developer mode is off: the hook says so on stderr and enforces as normal.
- The variable is read from the hook's own process environment, which the host sets at launch. Nothing in a project file can turn developer mode on.
- An installed copy from before requirement 8 does not know the record and keeps its hooks on until it is updated.
- `hooks/skill_passed.py` was first left out and then included at the user's request on 2026-11-27, so all registered hooks have the early exit.

## Testing Requirements

Each registered hook, run as the host runs it:

- variable set, in the toolkit repo: exits 0 with no output (session start: exits 0 and prints only the developer-mode notice);
- variable set, in another project: behaves as normal;
- variable not set, in the toolkit repo: behaves as normal;
- variable set, toolkit repo, a sibling module made unimportable: still exits 0;
- variable set, toolkit repo, an active run: no gate integrity starting record is written.

The switch, for worktrees: on in a linked worktree of the toolkit and when launched in one and working in the other; off in a worktree of another project, in a submodule or nested repository inside the toolkit, and in a folder whose `.git` file points at the toolkit without the toolkit naming it back.

An installed copy, run as the host runs it: steps aside in the recorded toolkit and in a worktree of it; keeps refusing with no record, in another project, without the variable, when launched in another project, and when the record names a folder that is not a toolkit checkout; never writes the record itself.

The test suite itself must behave the same whether or not the developer launched with the variable set.
