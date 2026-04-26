# Agent Toolkit — Pending Fixes and Improvements

## Must Fix (broken in practice)

| # | Issue | Fix | Files |
|---|-------|-----|-------|
| 1 | Architecture checks "Existing Codebase Constraints" but requirements generates "Codebase Index" | Replace section name in architecture | architecture/SKILL.md |
| 2 | "AskUserQuestion tool" doesn't exist in Claude Code | Replace with "Ask the user" | requirements/SKILL.md + 4 sub-skills |
| 3 | 20-question budget has no cross-sub-skill tracking | Pass "Questions remaining: N" when reading sub-skills | requirements/SKILL.md + 4 sub-skills |
| 4 | Topic-to-filename not normalized (spaces break lookups) | Add slug step: strip special chars, spaces to hyphens, lowercase | All base SKILL.md files |

## Should Fix (confusion or inefficiency)

| # | Issue | Fix | Files |
|---|-------|-----|-------|
| 5 | G5 file extension whitelist blocks code files skills need to read | Clarify: applies to user-provided external files only | shared/guardrails.md |
| 6 | G-IMPL-3 file overwrite protection conflicts with TDD refactor | Add current-slab exemption | shared/guardrails.md |
| 7 | TDD cycle instructions duplicated across 3 files | Sub-skills reference base instead of repeating | implementation/backend.md, frontend.md |
| 8 | Agent invocation syntax wrong ("Spawn Agent tool") | Use correct: "Agent tool with subagent_type X" | requirements/SKILL.md, frontend.md, ml.md |
| 9 | No blank-arguments handling | Add "If blank, ask what topic" to each base | All base SKILL.md files |
| 10 | No small-project escape hatch | Add "If trivial, just build it" option | implementation/SKILL.md |

## Design Gaps

| # | Issue | Fix | Files |
|---|-------|-----|-------|
| 11 | No debug/fix mode | Add Fix Mode to implementation | implementation/SKILL.md |
| 12 | No refactor mode | Add Refactor Mode to implementation | implementation/SKILL.md |
| 13 | Mode not passed to sub-skills | Prepend mode + budget context when reading sub-skills | requirements/SKILL.md |
| 14 | Codebase scan size limit missing | Add 3-level depth, 100-file cap | requirements/SKILL.md |
| 15 | Emojis remain in arch sub-skills (54) + engineering-principles (22) | Replace with text markers | 8 architecture files |
| 16 | architecture/backend.md over 400 lines (409) | Split into backend-data.md and backend-api.md | architecture/ |

## Skill Restructure

| # | Change | Details |
|---|--------|---------|
| 17 | Create codestructure-analyzer agent | Replaces inline codebase scan in requirements feature mode. Reusable by all skills. |
| 18 | Remove /test skill, merge into /reviewer | /reviewer = code structure + test coverage + write tests + code validity + security review |
| 19 | Remove test-generator agent | Absorbed by /reviewer |
| 20 | Remove code-reviewer agent | Absorbed by /reviewer |
| 21 | Update /evaluate for between-skill checkpoints | Add guidance that it runs between any skills, not just at end |
| 22 | Auto-invoke researcher on "idk" | requirements + architecture auto-launch appropriate agent when user says idk |

## Code Structure Standards (research done, needs encoding)

| # | Decision | Details |
|---|----------|---------|
| 23 | Co-located tests vs mirror directory | Research favors co-location (service.test.ts next to service.ts). User preference: TBD |
| 24 | Skeleton project structure | src/ for code, co-located unit tests, tests/ for integration/e2e, infra/ for deployment. CLAUDE.md at root. |
| 25 | Encode structure in skeleton.md | Update implementation/skeleton.md with the standard project layout |
| 26 | 400-line max per file | Enforce across all skills — currently only architecture/backend.md exceeds (409) |
