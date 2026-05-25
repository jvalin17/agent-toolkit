# Install & updates

## First install (Claude Code)

```bash
git clone https://github.com/jvalin17/agent-toolkit.git
cd agent-toolkit
./install.sh
```

**Requires:** `python3`, `jq`, Claude Code.

| Action | Result |
|--------|--------|
| Symlinks skills | `~/.claude/skills/` |
| Symlinks agents + shared | `~/.claude/agents/`, `~/.claude/shared/` |
| Registers hooks | `~/.claude/settings.json` |
| Bootstraps gates (in a git repo) | `gates.json`, `.agent-toolkit/` in project root |

Then open your project and run `claude`. You should see **"AGENT TOOLKIT ACTIVE"**.

## What install does NOT do every day

Re-run full `./install.sh` only for:
- First-time setup
- Symlink conflicts (skill exists as real directory)
- Missing `jq` on first attempt
- Stale symlinks pointing at wrong path

Day-to-day updates are automatic (see below).

## Automatic updates (Claude Code)

| Trigger | What runs |
|---------|-----------|
| Session start / after compact | `session_init.py` → `update.sh` |
| Every skill (`/precommit`, …) | `update.sh` |

`update.sh` runs `git pull` + `install.sh --sync-only` (retries twice, logs failures to stderr, **exits 1** if either step fails after retries), which:
- Symlinks new skills/agents/shared
- Merges new hooks into `settings.json`
- Refreshes hook paths if you moved the clone
- Re-syncs `.agent-toolkit/gate/` and merges missing `gates.json` keys

Disable auto-pull: `AGENT_TOOLKIT_AUTO_PULL=0`

## Manual update

```bash
cd /path/to/agent-toolkit && git pull && ./install.sh --sync-only
```

Start a **new Claude session** after updating if hooks behave oddly.

Debug sync: `AGENT_TOOLKIT_SYNC_VERBOSE=1 ./install.sh --sync-only`  
Sync logs from auto-update: check stderr for `update.sh:` lines if hooks seem stale after a network blip.  
Hook callers keep the session running on failure (`|| true` in settings.json) but stderr is no longer suppressed.

## Check config

```bash
agent-toolkit-setup --status    # in a project with gates.json
```

## Why two gate copies?

Hooks run from the toolkit repo (always latest). `.agent-toolkit/gate/` is copied into your project so CI and signed attestation work without the full toolkit checkout.

## Non-Claude projects

No `./install.sh` required. See [other-llms.md](other-llms.md).
