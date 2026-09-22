# Impact Analysis — Semantic Reference Tracing

Run this **before** modifying any function, parameter, data shape, or domain concept.
Used by: `/implementation` refactor mode, `/debug_tool` before fixes, `/assess` safe refactoring.

## When to Run

- Changing a function signature, return type, or behavior
- Renaming or removing a parameter, field, or constant
- Changing validation rules or business logic
- Modifying a data shape (API response, DB schema, config structure)

## Step 1: Identify Change Terms

Extract the **domain terms** affected by your change. Not just the function name — the *concepts*.

```
Example: changing `calculate_bid(amount, type)` to `calculate_bid(amount, type, currency)`

Change terms: "bid", "calculate_bid", "bid_amount", "bid_type", "amount", "currency"
```

Include: function name, parameter names, related domain words (synonyms, abbreviations, plurals).

## Step 2: Semantic Grep

For EACH change term, search the entire codebase:

```
grep -rn "bid" --include="*.py" --include="*.ts" --include="*.js" ...
```

Search in ALL of these:
- **Code**: function calls, imports, variable names, type annotations
- **Tests**: test names, fixtures, assertions, mock data
- **Comments**: `# bid must be positive`, `// assumes bid is in USD`
- **Config**: env vars, constants, config keys
- **Docs**: README, API docs, architecture docs
- **SQL/queries**: column names, WHERE clauses, JOIN conditions

## Step 3: Classify Each Reference

For every hit, classify it:

| Category | Action |
|----------|--------|
| **Direct caller** — calls the function you're changing | Must update. Test after. |
| **Indirect consumer** — uses the output downstream | Check if data shape/semantics changed. |
| **Constraint comment** — documents an assumption (`# bid > 0`) | Verify assumption still holds. |
| **Test fixture** — hardcoded test data | Update if input/output shape changed. |
| **Parallel implementation** — similar logic elsewhere | Flag for consistency. May need same change. |
| **Unrelated homonym** — same word, different meaning | Skip. |

## Step 4: Impact Report

Present findings BEFORE making changes:

```
IMPACT ANALYSIS: <what's changing>

Direct callers (MUST update):
  - src/auction.py:45 — calls calculate_bid(amount, type)
  - src/api/routes.py:112 — passes bid_amount to endpoint

Indirect consumers (CHECK):
  - src/reporting.py:78 — reads bid result for summary report
  - templates/bid_confirmation.html:23 — displays bid amount

Constraint comments (VERIFY):
  - src/validation.py:15 — "# bid_amount must be positive integer"
  - src/auction.py:30 — "# sealed bids cannot be modified after submission"

Test fixtures (UPDATE):
  - tests/test_auction.py:12 — fixture has bid_amount=100, no currency
  - tests/fixtures/bids.json — 5 bid records without currency field

Parallel implementations (FLAG):
  - src/legacy/old_bidding.py:67 — similar bid calculation, different path

Risk: [LOW|MEDIUM|HIGH] — based on number of direct callers and constraint violations
```

## Step 5: Proceed or Escalate

- **LOW risk** (< 5 references, no constraint violations): proceed with change
- **MEDIUM risk** (5-15 references or constraint comments affected): proceed carefully, update all references in same commit
- **HIGH risk** (> 15 references, multiple constraint violations, parallel implementations): ask user before proceeding. Consider breaking into smaller changes.

## Rules

- NEVER skip this for refactors. "I'll just rename this function" has broken more codebases than any bug.
- Comments are evidence. A comment saying `# must be called before X` is a dependency even if no code enforces it.
- Include test files. Stale test fixtures cause false passes — the most dangerous kind of test failure.
- When in doubt, include the reference. False positives are cheap; missed dependencies are expensive.
