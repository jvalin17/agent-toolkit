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
- Added 2026-11-28. Every developer-mode session start closes `~/.agent-toolkit/` to other accounts (folder `0700`, record `0600`), also when the folder was made earlier and when the record is already right. Permissions are never changed through a link or on an entry another account owns. A record write that fails removes the draft file it created; a file already waiting at the draft name is not touched.
- Added 2026-11-28, at the user's decision ("close them"). `path_protection` also refuses a write that names the folder without spelling it out. It runs and expands nothing: text decided at run time counts as "anything", letter case is ignored, and the only question is whether a name in the command could become the folder's. It looks at (1) a name starting `.agen` (a glob that fits, a variable spliced in, a string cut off mid-name); (2) a name directly under the home folder, however the home folder is written: a dotted one, one put together at run time (`~/$a$b`, `~/${v%x}`), or the pattern of a `find` that acts; and, wherever it points, an unquoted dotted glob with a letter in it that fits (`cd ~ && rm -rf .a*`); (3) the record's file name, `dev-repo`, inside a folder that is hidden, globbed or pieced together, or as the bare target of a redirect. For this check a command on the read-only list counts as a write when it is told to delete, write or run something: `find -delete/-exec/-fprint`, `sort -o`, `git config`, a command substitution, `awk` calling `system`. Reading through such a name stays allowed.
- The cost, accepted and pinned by tests: a few writes that could become the folder by their text alone are refused with the same "ask the user" message although they would not (`mkdir ~/.agent-$USER`, `touch ~/.$PROFILE`, `rm .a*` in a project, `echo ".agent-*" >> .gitignore`, code that creates a folder called exactly `'.agent'`). Ordinary commands that only share a word, a prefix or a regular expression with it are allowed and pinned too.
- Stated limit: a command that shows none of these is not seen. Known examples: the name written out differently and changed in code (`'.agent-x'.replace('x', 'toolkit')`, character codes), a glob inside interpreter code under a home folder the code looks up, a loop over every dotted folder after `cd ~`, a `find` that selects the record by its own name, a script kept in a file. No reading of the command text can close these; the stated limit on the record above still holds for them.
- Not changed here, and open for every protected path, not only this folder: the general read-only list still treats a command substitution, `find -exec`, `sort -o` and `awk` as reading (`echo $(rm -rf .gates)` passes). Whether to tighten that list is the user's decision.
- Added 2026-11-28. A record is not written into a real `~/.agent-toolkit` folder that another account owns: whoever owns the folder could rewrite it. Session start says so on stderr and an installed copy keeps its hooks on.
- Stated limit, kept by the user 2026-11-28: a project that copies the toolkit's `hooks/` folder to its own git root is, for those hooks, a checkout of its own. Launched with the variable, its copied hooks step aside, its session start writes a record naming it, and an installed copy then steps aside there too. Nothing inside a project can tell such a copy from the toolkit, and the person who copies the hooks and sets the variable is switching off their own enforcement. Hooks copied below the git root are an installed copy and do not count.
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

The record on disk: folder and record are for the owner only when created; an existing looser folder or record is closed at the next session start; nothing is changed through a link; a failed write leaves no draft, and a file already at the draft name is left alone.

Worktrees recorded with relative paths count like any other. A worktree moved by git stays on; one moved by hand is off until `git worktree repair`; another project placed where a moved worktree used to be is off.

The copied-hooks limit above is pinned by tests, so a change to it is a decision and not an accident.

The test suite itself must behave the same whether or not the developer launched with the variable set.
