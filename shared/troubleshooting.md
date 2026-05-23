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

## Gate blocks commit but you've run /precommit

**Symptom:** `git commit` blocked even after running `/precommit`.

**Check:** `.gates/precommit-passed` must contain `READY`. Verify:
```bash
cat .gates/precommit-passed
```

If missing or empty, run `/precommit` again.

## auto_continue.py doesn't restart

**Symptom:** Wrapper exits instead of looping.

**Check:** HANDOFF.md must exist and NOT contain `## COMPLETE` as a section header. The wrapper stops when it sees that marker or when HANDOFF.md is deleted.
