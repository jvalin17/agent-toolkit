# Troubleshooting

## Session immediately shows "HARD STOP" or timeout on start

**Symptom:** You start a fresh `claude` session and it immediately fires session limit warnings or blocks tools.

**Cause:** `.session/state.json` has stale data from a previous session (e.g. `stopped: 2`). This happens when `session_init.py` fails to run on SessionStart — usually an import error when running from a different project directory.

**Fix:**
```bash
rm -rf .session
```
Then start a new `claude` session. `session_init.py` will create fresh state.

**Prevention:** The import fix in commit `e56f458` ensures `session_init.py` works from any CWD. If you see this again, run `update.sh` or `git pull` in the toolkit directory to get the latest hooks.

## Hook not firing / no skill routing / no TDD reminders

**Symptom:** Hooks don't seem to run — no skill routing, no TDD checks, no session monitoring.

**Fix:**
```bash
cd /path/to/agent-toolkit && ./install.sh
```
This re-registers hooks in `~/.claude/settings.json`.

## "MISSING hook" warnings on session start (wrong directory)

**Symptom:** Session start shows `HARNESS INTEGRITY WARNINGS: MISSING hook: gate_hook.py` even though `./install.sh` ran successfully.

**Cause:** Hooks live in the **agent-toolkit clone** (e.g. `/path/to/agent-toolkit/hooks/`) and are registered in `~/.claude/settings.json`. They are **not** under your project's `hooks/` directory.

**Fix:** Run `./install.sh` from the toolkit clone. If warnings persist, check that `~/.claude/settings.json` contains commands pointing at your toolkit path. Re-run `./install.sh` to dedupe stale entries.

## finalize_report runs tests from wrong directory / wrong Python

**Symptom:** `/precommit` finalize passes but tests didn't actually run, or `python3` can't find your venv packages.

**Cause:** `finalize_report.py` must run test/lint against the **git project root**, not the shell's last `cd`. Custom `test_command` values using bare `python3` may hit system Python instead of the active venv.

**Fix:**
1. Re-run finalize from your project — it resolves git root from the `.scratch/.../findings.json` path (not shell cwd).
2. If you set a custom `test_command` with `python3`, it is rewritten to the active interpreter (venv-safe).
3. Omit `test_command`/`lint_command` to use auto-detect, or set project-specific values in your `gates.json`.

## Gate blocks commit but you've run /precommit

**Symptom:** `git commit` blocked even after running `/precommit`.

**Check:** `.gates/precommit-passed` must contain `READY`. Verify:
```bash
cat .gates/precommit-passed
```

If missing or empty, run `/precommit` again.

## Skill tool: "cannot be used due to disable-model-invocation"

**Symptom:** `/debug` or `Skill(debug)` fails with:
```
Skill debug cannot be used with Skill tool due to disable-model-invocation
```

**Cause:** Known Claude Code behavior — the Skill tool is invoked twice (slash command loads the skill, then the model calls Skill tool again). Toolkit skills set `disable-model-invocation: false` explicitly; the error can still appear on some Claude Code versions.

**Fix (pick one):**

1. **Use Read, not Skill tool** — tell the agent:
   ```
   Read skills/debug/SKILL.md and follow it step by step. Do not use the Skill tool.
   ```
2. **Re-link skills** — symlinks may point at a stale clone (`/tmp/...`):
   ```bash
   cd /path/to/agent-toolkit && ./install.sh
   ```
3. **Start a new session** after `./install.sh` so Claude picks up updated skill frontmatter.

**Workaround for any skill:** Natural language + Read the SKILL.md file always works; slash commands may still trigger the Skill tool error until Claude Code fixes the double-invocation bug.

## auto_continue.py doesn't restart

**Symptom:** Wrapper exits instead of looping.

**Check:** HANDOFF.md must exist and NOT contain `## COMPLETE` as a section header. The wrapper stops when it sees that marker or when HANDOFF.md is deleted.
