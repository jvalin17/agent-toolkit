# Requirements: developer-mode

Decided by the user 2026-11-27.

## Problem Statement

The toolkit's hooks run live from this repo's `hooks/` folder. While the toolkit itself is being changed, its own hooks police the work: a half-edited helper can crash every hook, and the gates built for user projects block edits to the gates themselves.

In the user's words: "we should have a developer mode where we don't apply the toolkit." On the switch: "launch variable and toolkit repo only." And: "just fix the dev mode where agent toolkit's own hooks don't block our way."

## Functional Requirements

| # | Requirement | Priority |
|---|-------------|----------|
| 1 | Developer mode is on only when the host was launched with `AGENT_TOOLKIT_DEV=1` | must |
| 2 | Developer mode is on only when the project being worked in is the toolkit the hooks were loaded from: the git top level of the working directory equals the parent of the running hook's `hooks/` folder. In any other project the variable does nothing | must |
| 3 | When on, every registered hook exits at once with success and applies nothing, including `check_doc_write.sh` | must |
| 4 | The early exit comes before any other import of the hook, so a half-edited sibling module cannot crash a hook. The check lives in a small module that uses the standard library only | must |
| 5 | Session start prints that developer mode is on and the toolkit is not applied | must |
| 6 | `/precommit` still runs by hand | must |
| 7 | No gate integrity starting record is written in developer mode | must |

## Boundaries

- This is the one exception to "an environment variable may only strengthen" (`mode_resolver`, `gate_hook`). The code says so where the check lives.
- Narrower than requirement 2, never wider (added after review, 2026-11-27): where the host names the folder it was launched in (`CLAUDE_PROJECT_DIR`), that folder must be in the toolkit too, so a session started in a user's project keeps its hooks if the working directory later moves into the toolkit.
- A git worktree of the toolkit counts as another project, because its top level is not the folder the hooks were loaded from.
- A fault in the check itself (a broken or missing `hooks/dev_mode.py`) means developer mode is off: the hook says so on stderr and enforces as normal.
- The variable is read from the hook's own process environment, which the host sets at launch. Nothing in a project file can turn developer mode on.
- Developer mode covers the hooks loaded from this repo. A separately installed copy of the toolkit (for example an older plugin copy) runs its own hooks and is not affected until it is updated.
- `hooks/skill_passed.py` was first left out and then included at the user's request on 2026-11-27, so all registered hooks have the early exit.

## Testing Requirements

Each registered hook, run as the host runs it:

- variable set, in the toolkit repo: exits 0 with no output (session start: exits 0 and prints only the developer-mode notice);
- variable set, in another project: behaves as normal;
- variable not set, in the toolkit repo: behaves as normal;
- variable set, toolkit repo, a sibling module made unimportable: still exits 0;
- variable set, toolkit repo, an active run: no gate integrity starting record is written.

The test suite itself must behave the same whether or not the developer launched with the variable set.
