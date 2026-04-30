# Agent Toolkit — Future Work

## Planned: /explore skill

Get familiar with any project — or multiple projects. Works on repos you've never seen before.

**Proposed flow:**
1. Point it at a directory (or multiple): `/explore /path/to/repo`
2. Deep analysis:
   - Tech stack, framework, language, database
   - Project structure (key directories, patterns)
   - Features (what does this app do?)
   - Architecture (how is it built? what patterns?)
   - Data flow (how does a request travel through the system?)
   - Tests (what's covered? what framework?)
   - Recent changes (git log — what's been worked on?)
   - Known issues (TODOs, FIXMEs, open issues)
3. Output: full project-state.md + Codebase Index
4. Multi-repo mode: compare repos, find shared patterns, map dependencies

**How it differs from codestructure-analyzer agent:**
- Agent: shallow scan (stack, structure, conventions) — for feature mode
- /explore: deep dive (features, flows, issues, tests, history) — for understanding

**Use cases:**
- "I just cloned this repo, what is it?"
- "I have 3 repos, how do they relate?"
- "What's the state of this project? What works, what doesn't?"
- "I'm onboarding to a new codebase"

---

## Planned: /debug skill

Systematic debugging when something is broken and you don't know why.

**Proposed flow:**
1. User describes symptom ("multiplayer is broken", "page is blank")
2. Read project-state.md, architecture doc, recent git changes
3. Systematic diagnosis by layer:
   - Network: endpoint reachable? CORS? auth headers?
   - Data: DB has data? query returns results? response shape correct?
   - State: frontend state updated? race conditions? stale cache?
   - Async: event loop conflicts? silent failures? unhandled promises?
   - Config: env vars? port? feature flags? provider initialized?
   - Version: dependency conflicts? breaking changes?
4. Narrow down to specific file and function
5. Reproduce with a failing test
6. Fix and verify
7. Add regression test
8. Update project-state.md

**How it differs from /implementation fix mode:**
- Fix mode: "bug is in login.py line 34" -> write test, fix
- Debug mode: "multiplayer is broken, idk why" -> diagnose first, then fix

---

## Planned: readme-validator agent

Verifies everything claimed in a README is actually true.

**What it checks:**
- Install commands: do they actually work? (`npm install` succeeds? `pip install` succeeds?)
- Run commands: does the app start? (try `npm start`, `python main.py`, etc.)
- Endpoints mentioned: do they exist in the code? do they respond?
- Features listed: does the code actually implement them? (grep for relevant functions/components)
- File paths mentioned: do the files exist?
- Dependencies listed: are they in package.json / pyproject.toml?
- Environment variables: are they documented in .env.example?
- Screenshots / badges: do links resolve?
- Version numbers: do they match package.json / pyproject.toml?

**Output:**
```
README Validation: my-app

[PASS] Install: npm install succeeds
[PASS] Run: npm start serves on port 3000
[FAIL] Feature "dark mode" — searched for dark/theme/toggle — not found in code
[FAIL] Endpoint GET /api/health — not defined in any route file
[PASS] File structure matches what README describes
[WARN] .env.example missing DATABASE_URL (referenced in README but not in example file)

Accuracy: 8/10 claims verified
```

**When to run:**
- After /setup generates a README
- Before any release / push to public repo
- As part of /reviewer flow (optional)

---

## Priority order

1. `/explore` — needed first (other skills benefit from it)
2. `/debug` — high value for daily use
3. `readme-validator` — quality gate before shipping
