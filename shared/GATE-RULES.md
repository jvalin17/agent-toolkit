# Gate Rules (exhaustive)

These are the **only** things the precommit gate checks. If a requirement is not on this list, it does not exist. Do not invent additional requirements.

## Mechanical checks (run by finalize_report.py, not the agent)

1. **Tests pass** — `pytest` (or configured `test_command`) exits 0
2. **Lint passes** — `ruff` (or configured `lint_command`) exits 0
3. **Python naming: snake_case everywhere** — PEP 8, enforced by ruff. No camelCase in Python. No `# noqa` suppressions in test files.
4. **No noqa in test files** — adding `# noqa` to test files blocks the gate. Fix the lint issue instead of suppressing it.
5. **TDD: new functions need tests** — new functions in the diff must have corresponding test functions
6. **TDD ordering** — test files must be edited before source files (when TDD mode is active)
7. **Test plan coverage** — if `.scratch/test-plan_*.json` exists, every test case must have a matching test function. On pass, plan is auto-deleted and summary appended to `project-state.md`
8. **Test plan required** — if source files were edited, a test plan must exist (either in `.scratch/test-plan_*.json` or as a completed summary in `project-state.md`). Exempt: test files, hooks, scripts, config, docs, markdown. Write the plan BEFORE coding — see `/implementation` Step 4.
9. **Test plan ordering** — if a test plan was written, it must appear in the session JSONL *before* the first source file edit. Writing the plan after implementing → block. This is checked from JSONL timestamps and cannot be faked.

## Agent-reported checks (verified by finalize)

10. **Instructions addressed** — all user instructions marked as addressed
11. **No rule violations** — role rule violations count is 0
12. **README valid** — readme validation passed
13. **Tests meaningful** — test quality is not "sloppy"
14. **App verification** — not still "pending" (must be "done" or "skip")

## Toolkit infrastructure — do NOT modify

These are load-bearing design decisions. Do not work around them.

- **`reports/` is gitignored.** This is correct. Do NOT un-gitignore it. Do NOT commit report files. CI generates reports at runtime via `ci-generate-reports.py`. If CI can't find reports, fix the generator — don't commit stale reports.
- **`ci-generate-reports.py` is self-contained.** It does NOT need `finalize_report.py`. It uses `gate/attest.py` directly. If it can't find the gate module, check that `install.sh` ran correctly (`ls .agent-toolkit/gate/attest.py`).
- **`.gates/` is gitignored.** Gate flags are written by `finalize_report.py` at runtime. Do NOT create them manually.
- **`.session/` is hook-managed.** Never read, write, or delete files in `.session/`.
- **`finalize_report.py` is the only report writer.** The agent cannot write to `reports/` directly (G-REPORT-1).

If CI fails, read the actual error log (`gh run view <id> --log-failed`) before proposing any fix. Do NOT theorize about `.gitignore` or file visibility without evidence.

## What the gate does NOT check

- camelCase test names (Python uses snake_case — always)
- Code coverage percentage
- Number of test files
- Specific lint rules beyond what ruff enforces
- File naming conventions beyond what ruff checks
- Any requirement not listed above
