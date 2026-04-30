# Agent Toolkit — Future Work

## Planned: /debug skill

Dedicated skill for systematic debugging. Different from implementation's "fix mode" (which is for known bugs). /debug is for when something is broken and you don't know why.

**Proposed flow:**
1. User describes the symptom ("multiplayer is broken", "page is blank", "API returns 0 results")
2. Skill reads project-state.md, architecture doc, recent git changes
3. Systematic diagnosis:
   - Check logs/error output
   - Trace the data flow from symptom back to root cause
   - Identify the failing layer (frontend / API / backend / DB / external service)
   - Narrow down to specific file and function
4. Reproduce with a failing test
5. Fix and verify
6. Add regression test to prevent recurrence
7. Update project-state.md with the fix

**How it differs from /implementation fix mode:**
- Fix mode: "I know the bug is in login.py line 34" -> write test, fix it
- Debug mode: "multiplayer is broken, I don't know why" -> diagnose first, then fix

**Categories to check systematically:**
- Network: API endpoint reachable? Correct URL? CORS? Auth headers?
- Data: DB has expected data? Query returns results? Response shape matches frontend expectations?
- State: Frontend state updated after API call? Race conditions? Stale cache?
- Async: Event loop conflicts? Silent failures? Unhandled promise rejections?
- Config: Env vars set? Correct port? Feature flags? Provider initialized?
- Version: Dependency conflicts? Breaking changes in updates?

**Key principle from feedback:** A single systematic debugging session is more valuable than random fixes. Diagnose by layer, don't guess.
