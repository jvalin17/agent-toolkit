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

`update.sh` runs `install.sh --sync-only` (retries twice, logs failures to stderr, **exits 1** if it fails after retries), which:
- Symlinks new skills/agents/shared
- Merges new hooks into `settings.json`
- Refreshes hook paths if you moved the clone
- Re-syncs `.agent-toolkit/gate/` and merges missing `gates.json` keys

**Pulling from GitHub is opt-in.** Hooks run as you on every machine, so a push to the upstream repo must not silently become running code at your next session. Enable the pull deliberately:

```bash
export AGENT_TOOLKIT_AUTO_PULL=1    # update.sh then runs git pull --ff-only and prints what changed
```

## Manual update

```bash
cd /path/to/agent-toolkit && git pull && ./install.sh --sync-only
```

Start a **new Claude session** after updating if hooks behave oddly.

Debug sync: `AGENT_TOOLKIT_SYNC_VERBOSE=1 ./install.sh --sync-only`  
Sync logs from auto-update: check stderr for `update.sh:` lines if hooks seem stale after a network blip.  
Hook callers keep the session running on failure (`|| true` in settings.json) but stderr is no longer suppressed.

## Plugin install updates (Claude Code plugin)

If you installed via `claude plugin install agent-toolkit`, Claude Code refreshes the cached copy only when the plugin's computed version changes. The toolkit's manifests deliberately carry **no `version` field**, so the computed version is the commit SHA and every push to `main` is a new version:

```bash
claude plugin marketplace update agent-toolkit   # refresh the catalog
claude plugin update agent-toolkit               # pull the newest commit; restart to apply
```

Do not add `"version"` to `.claude-plugin/plugin.json` or `marketplace.json`: a pinned string keeps every user on the cached copy until it is bumped, however many commits land (`tests/test_plugin_manifest.py` guards this).

## Check config

```bash
agent-toolkit-setup --status    # in a project with gates.json
```

## Why two gate copies?

Hooks run from the toolkit repo (always latest). `.agent-toolkit/gate/` is copied into your project so CI and signed attestation work without the full toolkit checkout.

## Non-Claude projects

No `./install.sh` required. See [other-llms.md](other-llms.md).
