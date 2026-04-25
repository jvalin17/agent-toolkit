# TDD Patterns Reference

> **Our synthesis.** TDD cycles adapted per mode, based on established practices.
> Last verified: 2026-04-24

## Sources
- [Test Driven Development: By Example — Kent Beck](https://en.wikipedia.org/wiki/Test-Driven_Development_by_Example)
- [The Three Laws of TDD — Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2014/12/17/TheCyclesOfTDD.html)
- [Testing Trophy — Kent C. Dodds](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)
- [Judgement-tests /write-tests skill](https://github.com/jvalin17/judgement-tests) — patterns adapted from this project

---

## Classic TDD Cycle (Backend)

```
RED:    Write a test that describes expected behavior. Run it. It MUST fail.
GREEN:  Write the MINIMUM code to make the test pass. Nothing more.
REFACTOR: Clean up the code without changing behavior. Tests still pass.
REPEAT: Next behavior.
```

### Rules
1. You may not write production code unless it makes a failing test pass.
2. You may not write more of a test than is sufficient to fail.
3. You may not write more production code than is sufficient to pass the current failing test.

### Block Size
Each TDD cycle should be small — one function, one endpoint, one behavior.
- ✅ "Test that creating a job returns 201 with the job ID"
- ❌ "Test the entire job search pipeline end-to-end" (too big for one cycle)

---

## Component TDD (Frontend)

Adapted for UI — render first, then interactions.

```
1. RENDER TEST: Write test that renders component with props. Confirm it shows expected content.
2. IMPLEMENT RENDER: Build the component JSX/HTML to pass.
3. INTERACTION TEST: Write test that simulates user action (click, type). Confirm correct behavior.
4. IMPLEMENT INTERACTION: Add event handlers to pass.
5. STATE TEST: Write test that verifies state changes correctly.
6. IMPLEMENT STATE: Add state management to pass.
7. REFACTOR: Clean up component.
```

### Frontend-Specific Rules
- Test behavior, not implementation (don't test internal state directly)
- Use `getByRole`, `getByText` over `getByTestId` when possible
- Always include provider wrappers if component uses context
- Test loading, error, and empty states — not just happy path

---

## Threat-Driven TDD (Security)

Attack first, then defend.

```
1. THREAT: Identify a specific attack vector (SQL injection on login)
2. ATTACK TEST: Write a test that simulates the attack
3. RUN: Confirm the attack currently succeeds (or would succeed)
4. DEFEND: Implement the defense (parameterized queries, input validation)
5. RUN: Confirm the attack test now passes (attack is blocked)
6. REGRESSION: Ensure legitimate operations still work
```

### Security Test Categories
- **Authentication:** valid/invalid/expired/missing tokens
- **Authorization:** accessing other users' data, privilege escalation
- **Injection:** SQL, XSS, command injection, path traversal
- **Data exposure:** sensitive fields not in API responses, logs clean
- **Rate limiting:** repeated requests throttled

---

## Data-Contract TDD (ML/Data)

Validate data before validating models.

```
1. CONTRACT TEST: Define expected data schema (types, ranges, nulls)
2. VALIDATE: Implement schema validation to pass contract tests
3. TRANSFORM TEST: Define expected output of each data transform
4. IMPLEMENT TRANSFORM: Build transforms to pass
5. MODEL BEHAVIOR TEST: Define expected model outputs (accuracy threshold, output shape)
6. IMPLEMENT MODEL: Train/build model to pass behavior tests
7. INTEGRATION TEST: Raw data → full pipeline → prediction
```

### ML-Specific Rules
- Always use seeded randomness (`random.seed(42)`, `np.random.seed(42)`)
- Test model output SHAPE and TYPE, not exact values (models are non-deterministic)
- Set accuracy thresholds, not exact accuracy (e.g., "F1 > 0.85", not "F1 == 0.8723")
- Test with edge cases: empty dataset, single sample, all-same-class
- Data validation tests are MORE important than model tests

---

## Pipeline TDD (CI/CD)

Verify each stage independently.

```
1. SMOKE TEST: Define "what must work for this pipeline to be healthy?"
2. BUILD STAGE: Implement build step → verify it produces expected output
3. TEST STAGE: Implement test runner step → verify it runs and reports
4. DEPLOY STAGE: Implement deploy step → verify it reaches target
5. ROLLBACK: Implement rollback → verify previous version is restored
```

### Pipeline Test Categories
- **Build:** clean checkout builds successfully
- **Test gate:** failing tests block deployment
- **Deploy:** artifact reaches target environment
- **Health check:** deployed service responds correctly
- **Rollback:** previous version is restored on failure

---

## Common Anti-Patterns to Avoid

| Anti-Pattern | Problem | Fix |
|-------------|---------|-----|
| Testing implementation details | Test breaks on refactor | Test behavior/output instead |
| Too many mocks | Test doesn't test anything real | Use real dependencies when cheap |
| Test per method | Fragile, doesn't catch integration bugs | Test per behavior/scenario |
| Assertion-free test | Test always passes | Every test must have at least one assert |
| Flaky test | Passes sometimes, fails sometimes | Fix the root cause (timing, randomness, shared state) |
| Testing framework code | Testing that React renders, that pytest runs | Only test YOUR code |
