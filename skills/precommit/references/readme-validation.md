# README Validation (precommit Step 5b)

If `README.md` exists and staged changes affect features, endpoints, env vars, commands, or paths:

1. Invoke **readme-validator** in precommit mode
2. Check staged changes vs README claims
3. Auto mode: fix mode for factual drift (G-RM-1/2/3)
4. Interactive: report FAIL, user decides

Skip for test-only, docs-only, or config-only changes with no feature impact.

**BLOCKED example:** `README BLOCKED: [N] inaccurate claims found.`
