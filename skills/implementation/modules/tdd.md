# Implementation — TDD module

Pull this when writing or changing logic.

1. Write a failing test with specific assertions (not `assert True`).
2. Run tests — confirm failure matches the missing behavior.
3. Implement the minimum code to pass.
4. Re-run tests — green before next change.
5. Use realistic fixture data; cite provenance when required by project mode.

Fix mode: failing test → fix → verify (do not ask which mode).
Direct mode: still test-first for logic; wiring-only may scaffold without TDD.
