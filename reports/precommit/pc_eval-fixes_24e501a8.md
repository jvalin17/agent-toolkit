# Pre-commit report: eval findings fixes

**Date:** 2026-05-21
**Scope:** 4 eval findings — enforcement defaults, doc-guard wiring, doc-guard tests, session_monitor decomposition

## Fixes

1. **Enforcement default disagreement**: Aligned gate-unlock.md (was "warn") and gate.py fallback (was "warn") to match templates/gates.json and README ("block"). Updated test assertion.
2. **check_doc_write.sh not installed**: Added to install.sh (fresh-install JSON + incremental block). Removed bogus `--with-doc-guard` comment. Fixed path-resolution bug (non-existent parent dirs resolved to `/`).
3. **check_doc_write.sh untested**: Added 5 pytest tests (allow inside project, block outside, allow ~/.claude/, empty path, block message content). Tests caught real bug in path resolution.
4. **session_monitor.py god file (790 lines)**: Extracted strict_mode.py (132 lines) and auto_handoff.py (147 lines). session_monitor.py reduced to 542 lines (31% reduction). Updated test imports.

## Gate

```
Pre-commit report:
Instructions: 4/4 addressed
Test suite: 362 passed / 0 failed / 1 skipped (pre-existing cffi)
Test quality: 5 new meaningful tests + 109 existing, 0 sloppy
Principles: SOLID [ok] DRY [ok] KISS [ok] YAGNI [ok]
Standards: 5/5 passed
Rules: 0 violations
G-IMPL-6: 0 shortcuts
README: SKIPPED (no README changes in this commit)
App verification: N/A (hooks verified via test suite)

[x] READY TO COMMIT
[ ] BLOCKED
```
