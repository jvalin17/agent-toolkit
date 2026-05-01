# Guardrails — Quick Reference

One-line summaries. Read full `guardrails.md` only when a guardrail triggers or you need the detail.

## Universal (G1-G11)
- **G1:** No secrets in output — use env var placeholders
- **G2:** No destructive ops without user confirmation
- **G3:** State limitations clearly — "verified exists, can't verify works"
- **G4:** Warn if references older than 6 months
- **G5:** File safety check on user-provided external files (not project source code)
- **G6:** No real PII — use synthetic data
- **G7:** Flag gaps in external docs, don't refuse to work
- **G8:** Mid-conversation updates — update docs in place, don't restart
- **G9:** LLM data security — never send secrets to external LLMs, mark data exit points
- **G10:** Update README after feature changes
- **G11:** Check rules before acting — delegate to `rules-indexer`, flag contradictions

## Pre-commit (G-PC-1 to G-PC-5)
- **G-PC-1:** No sloppy tests — require specific value assertions
- **G-PC-2:** All user instructions addressed before commit
- **G-PC-3:** Never say "fixed" without verification
- **G-PC-4:** Verify in running app, not just tests
- **G-PC-5:** Ask on ambiguity, log concern in project-state.md

## Skill-specific
- **G-REQ-1/2/3:** 20 questions max, estimation disclaimers, ML data privacy
- **G-ARCH-1/2/3/4:** 2 backtracks, OWASP refs, OWASP LLM, 20 decisions max
- **G-IMPL-1/2/3/4/5:** No SQL concat, no hardcoded secrets, overwrite protection (exempt TDD), trusted packages, 1 file per cycle
- **G-EVAL-1/2:** Highlight unverifiable, guardrail-aware grading
- **G-UPD-1/2:** No auto-update, offline graceful
