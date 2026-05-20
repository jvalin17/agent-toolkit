# Project state — agent-toolkit

**Last updated:** 2026-05-20

## Resume in a new session

1. `rm -rf .session` in repo root (clears harness hard stop if tripped).
2. Read this file and [`README.md`](README.md). Gate details: [`shared/gate-unlock.md`](shared/gate-unlock.md).

## Current branch

`main` — legacy + warn + minimal by default (`gates.json`, `templates/gates.json`). Signed mode optional via `scripts/setup-signed-gates.sh`.

## Recently shipped

| Item | Commit / note |
|------|----------------|
| Eval follow-ups (hook tests, evaluate archive, README 50 min) | `103f6d3` |
| Hook suite | 55/55 `tests/test-hooks.sh` |
| Gate unit tests | 16/16 `tests/test_gate.py` |

## In progress (working tree)

| Item | Status |
|------|--------|
| README cleanup + gate mode examples | Modified locally |
| Eval report @ `103f6d3` (88% B+) | `reports/evaluate/` |
| Doc fixes: G-SESSION-1 in `guardrails.md`, `hooks/gates.json` schema, this file | Current session |

## Open work

- Commit README / guardrails / project-state / `hooks/gates.json` when ready.
- Optional: commit untracked `reports/assess`, `reports/precommit`, `reports/reviewer` if keeping CI fixtures in-repo.

## Tests

```bash
python3 -m pytest tests/test_gate.py -q
bash tests/test-hooks.sh
```
