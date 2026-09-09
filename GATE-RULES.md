# Gate Rules (exhaustive)

These are the **only** things the precommit gate checks. If a requirement is not on this list, it does not exist. Do not invent additional requirements.

## Mechanical checks (run by finalize_report.py, not the agent)

1. **Tests pass** — `pytest` (or configured `test_command`) exits 0
2. **Lint passes** — `ruff` (or configured `lint_command`) exits 0
3. **Python naming: snake_case everywhere** — PEP 8, enforced by ruff. No camelCase in Python. No `# noqa` suppressions in test files.
4. **No noqa in test files** — adding `# noqa` to test files blocks the gate. Fix the lint issue instead of suppressing it.
5. **TDD: new functions need tests** — new functions in the diff must have corresponding test functions
6. **TDD ordering** — test files must be edited before source files (when TDD mode is active)

## Agent-reported checks (verified by finalize)

7. **Instructions addressed** — all user instructions marked as addressed
8. **No rule violations** — role rule violations count is 0
9. **README valid** — readme validation passed
10. **Tests meaningful** — test quality is not "sloppy"
11. **App verification** — not still "pending" (must be "done" or "skip")

## What the gate does NOT check

- camelCase test names (Python uses snake_case — always)
- Code coverage percentage
- Number of test files
- Specific lint rules beyond what ruff enforces
- File naming conventions beyond what ruff checks
- Any requirement not listed above
