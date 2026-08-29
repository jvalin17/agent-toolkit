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

If missing or empty, run `/precommit` again (including the `finalize_report.py` step).

## Gate blocks push but you've run /evaluate

**Symptom:** `git push` blocked even after running `/evaluate`.

**Check:** `.gates/evaluate-passed` must contain `PASSED` and a score ≥ `eval_threshold` in `gates.json` (default 95). Verify:
```bash
cat .gates/evaluate-passed
grep eval_threshold gates.json
```

With default **`gate_protect: true`**, only `finalize_report.py` writes this file — run:
```bash
python3 hooks/finalize_report.py evaluate .scratch/evaluate_<slug>/findings.json
```
Exit code 0 means the gate unlocked; exit code 1 means score or mechanical checks blocked.

## Gate flags cleared after commit vs push

**Symptom:** Ran `/evaluate` and finalized, committed, but expected to push without re-running evaluate.

**Expected:** `gate_cleanup.py` clears only `precommit-passed` on commit. Push-scoped flags (`evaluate-passed`, etc.) should still exist. If missing, re-run finalize for the skill.

**Symptom:** Push succeeded but next push requires fresh evaluate.

**Expected:** Push clears push-scoped flags. Re-finalize evaluate (and reviewer/assess per profile) before the next push.

## Skill tool: "cannot be used due to disable-model-invocation"

**Symptom:** `/debug_tool` or `Skill(debug_tool)` fails with:
```
Skill debug_tool cannot be used with Skill tool due to disable-model-invocation
```

**Cause:** This is a **Claude Code platform bug**, not a toolkit bug. The Skill tool double-invokes: the slash command loads the skill prompt, then the model calls the Skill tool again, which triggers the `disable-model-invocation` guard. Setting the frontmatter to `false` is necessary but **not sufficient** — the error can still appear on some Claude Code versions regardless of the setting.

**Status:** All 13 toolkit skills have `disable-model-invocation: false`. A regression test (`tests/test_skill_frontmatter.py`) enforces this. The `/debug_tool` routing hook (`hooks/route_to_skill.py`) includes a permanent workaround that tells the model to use `Read` instead of the Skill tool.

**If you hit this error:**

1. **Do nothing** — the routing hook already handles it. When the hook detects a debug task, it injects "Read skills/debug_tool/SKILL.md" instead of using the Skill tool. This is the primary mitigation.
2. **Re-link skills** if symlinks are stale:
   ```bash
   cd /path/to/agent-toolkit && ./install.sh
   ```
3. **Start a new session** after `./install.sh` so Claude picks up updated skill frontmatter.

**For any skill:** `Read skills/<name>/SKILL.md` and following it step by step always works. Slash commands may still trigger the double-invocation error until the Claude Code platform fixes it upstream.

## auto_continue.py doesn't restart

**Symptom:** Wrapper exits instead of looping.

**Check:** HANDOFF.md must exist and NOT contain `## COMPLETE` as a section header. The wrapper stops when it sees that marker or when HANDOFF.md is deleted.
