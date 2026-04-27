# Tests Review
Keywords: test, coverage, unit, integration, regression, e2e, assertion, mock, fixture

For guardrails and principles, see main SKILL.md.

## Step 1: Coverage Analysis

Detect the test framework (jest, vitest, pytest, go test, cargo test, etc.) and existing test patterns.

For each file in the target, build a coverage table:

> | File | Methods/Functions | Tested | Untested | Risk |
> |------|------------------|--------|----------|------|
> | user.py | 8 | 3 | 5 | High — auth logic |
> | search.py | 4 | 0 | 4 | High — core feature |
> | Button.tsx | 3 interactions | 0 | 3 | Medium — UI |

Present this and ask:
> "Want me to: **write all missing tests**, **prioritize by risk**, or **test specific files**?"

## Step 2: Write Missing Tests

### Test data rules

**Never use placeholder data:**
```
name = "test"           # NO
email = "test@test.com" # NO
amount = 123            # NO
id = "abc"              # NO
```

**Always use realistic synthetic data:**
```
name = "Maria Garcia"
email = "m.garcia@outlook.com"
amount = 47.99
product = "Wireless Bluetooth Headphones"
address = "742 Evergreen Terrace, Springfield, IL 62704"
```

**Edge case data (use real-world examples):**
```
# Names
"Bjork Gudmundsdottir"          # Icelandic
"Jose Garcia-Lopez"             # Hyphenated
"Wei Zhang"                     # Short
"Dr. Sarah O'Brien-Mitchell"    # Prefix + apostrophe + hyphen

# Emails
"user+tag@gmail.com"            # Plus addressing
"name@company.co.uk"            # Multi-part TLD

# Boundaries
price = 0.01                    # Minimum
price = 99999.99                # Maximum
price = 0.00                    # Zero
price = -1.00                   # Negative (reject)

# Attack strings
"'; DROP TABLE users; --"       # SQL injection
"<script>alert(1)</script>"     # XSS
"" (empty string)               # Empty
"a" * 10000                     # Very long
```

### What to test per code type

**Backend (functions, methods, classes)** — for EACH public method:
- Happy path with valid input
- Each validation rule (empty, invalid format, out of range)
- Duplicate/conflict handling
- Edge cases (unicode, boundaries, very long input)
- Error paths (what exceptions are thrown and when)
- Return value shape (correct fields, correct types, no leaking internals)

**Frontend (components, pages)** — for EACH component:
- Renders correctly with expected props
- Each user interaction (click, type, submit, hover)
- Loading, error, and empty states
- Conditional rendering (what shows/hides and when)
- Accessibility (labels, keyboard focus, ARIA)

**API endpoints** — for EACH endpoint:
- Success response (status code, body shape)
- Each error case (400, 401, 403, 404, 429)
- Input validation (missing fields, wrong types, too long)
- Edge cases (special characters, empty arrays, null values)
- Pagination if applicable

### Test structure

Match the project's existing structure. If none exists:
```
tests/
  unit/          # One test file per source file
  integration/   # Cross-module and API tests
  e2e/           # End-to-end flows
```

### Writing rules

1. One concern per test. Test name describes exactly what it verifies.
2. Arrange-Act-Assert pattern. Clear separation.
3. No test interdependence. Each test runs in isolation.
4. Specific assertions — check exact values, not just truthiness.
5. Test behavior, not implementation. Tests survive refactoring.
6. Follow the project's existing test style (naming, setup, mocking patterns).

## Step 3: Regression Tests

Identify critical flows from `project-state.md` or by reading the code:
- User-facing flows (signup, login, core feature, logout)
- Data flows (CRUD operations end-to-end)
- Payment/transaction flows
- Error recovery flows

Write at least one regression test per critical flow. These test the full path, not individual units.

## Step 4: End-to-End Test (Mandatory)

Write at least ONE e2e test that exercises the primary user flow with realistic data. This test:
- Sets up real (or realistic mock) data
- Walks through the core user journey
- Asserts on final state, not intermediate steps
- Uses realistic data throughout (names, emails, amounts — no placeholders)

## Step 5: Run and Report

1. Run ALL tests (existing + new): `npm test`, `pytest`, `cargo test`, etc.
2. If tests fail against existing code — that's a bug. Report it. Do NOT change the test.
3. If tests fail due to setup issues (missing DB, missing env var) — fix setup, not the test.

Report results:

> | Category | Tests | Passing | Failing | New |
> |----------|-------|---------|---------|-----|
> | Unit | 47 | 47 | 0 | 32 |
> | Integration | 12 | 11 | 1 | 8 |
> | E2E | 1 | 1 | 0 | 1 |
> | **Total** | **60** | **59** | **1** | **41** |
>
> **Bugs found:**
> - `search.py:34` — returns 500 when query contains unicode characters
>
> **Coverage:** 23% -> 78%

## Live Integration Tests

Every external API integration needs at least 1 live test with a separate marker:

```python
@pytest.mark.live  # Only runs with: pytest -m live
def test_jsearch_returns_results():
    results = search_jobs("python developer", "remote")
    assert len(results) > 0
    assert results[0].title  # not empty
```

- Use `@pytest.mark.live` (Python) or `describe.skip` / test tags (JS) to isolate from unit tests
- Live tests verify the real API works end-to-end — they catch silent failures that mocks miss
- Don't include in default `pytest` / `npm test` — run separately
- Minimum 1 live test per external service

## Test File Header

Add a comment block at the top of each new test file:
```
/**
 * Tests for [module/component]
 * Covers: [brief list]
 * Not covered: [anything skipped and why]
 * Test data: synthetic — no real PII
 */
```
