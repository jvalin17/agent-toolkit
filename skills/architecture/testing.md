# Testing Architecture

Decisions for the testing strategy of the system. Always relevant — every system needs testing, even prototypes.

## Inputs

Read `requirements/<name>.md` and extract:
- **Testing Requirements** section — coverage targets, required test types, compliance needs
- **Required Test Types** table — which types of tests are expected (unit, integration, e2e, etc.)
- **Regression Policy** — what runs on every PR vs nightly vs manually
- **CI/CD Expectations** — pipeline stages, deployment targets, automation level

If the Testing Requirements section exists, use the user's stated testing level, required test types, and CI/CD expectations as input. Do not re-ask what was already decided.

Also read the Quick Architecture from `architecture/<name>.md` for the chosen tech stack and architecture pattern.

---

### Decision 1: Test Pyramid Split

**Context:** How testing effort is distributed across layers. The foundational testing decision — sets the ratio for everything else.

**Options:**

| | Option A: API-Heavy Split | Option B: UI-Heavy Split | Option C: ML-Heavy Split | Option D (local/cheap): Minimal Viable Testing |
|---|---------|---------|---------|---------|
| What | 60% unit / 30% integration / 10% e2e | 50% unit / 20% integration / 30% e2e | 40% unit / 30% integration / 20% model eval / 10% e2e | 80% unit / 20% integration / 0% e2e |
| Best for | Backend services, APIs, data processing | Frontend-heavy apps, user-facing products | ML/AI products with model quality requirements | Prototypes, MVPs, solo developers |
| Trade-off | Less UI coverage, relies on integration tests catching UI issues | More e2e tests = slower CI, more flaky tests | Model evaluation is expensive and slow | No end-to-end confidence, but fast feedback |
| Cost | Moderate CI time | Higher CI time (e2e is slow) | Highest (GPU for model eval, large datasets) | Lowest CI time |
| SOLID/DRY check | ✅ Clear boundaries per layer | ✅ Covers user journeys | ✅ Includes model-specific quality | ⚠️ Gaps in coverage |

**Adjust based on testing level from requirements:**
- **Basic:** Fewer layers, focus on critical paths only
- **Standard:** Full pyramid as described above
- **Rigorous:** All layers plus mutation testing, property-based tests, chaos testing

**Consequence:** Shapes framework selection, CI pipeline design, and testing infrastructure.

---

### Decision 2: Test Framework Selection

**Context:** Which tools to use for each test layer. Depends on pyramid split (Decision 1) and tech stack.

**Options by stack:**

| Stack | Unit Testing | Integration Testing | E2E Testing |
|-------|-------------|-------------------|-------------|
| **JavaScript/TypeScript** | Vitest, Jest | Supertest, Testing Library | Playwright, Cypress |
| **Python** | pytest | pytest + httpx/TestClient | Playwright, Selenium |
| **Go** | testing (stdlib) | testing + httptest | Playwright, k6 |
| **Java/Kotlin** | JUnit 5, Kotest | Spring Boot Test, TestContainers | Playwright, Selenium |
| **Rust** | cargo test (built-in) | cargo test + reqwest | Playwright |
| **Ruby** | RSpec, Minitest | RSpec + rack-test | Capybara, Playwright |

**Selection criteria:**
- Prefer the ecosystem default (less friction, more examples)
- Prefer frameworks with watch mode for development
- Prefer Playwright over Selenium for new projects (faster, more reliable)

**Must align with CI/CD expectations from requirements.** If requirements specify "tests must run in < 5 minutes," choose faster frameworks and fewer e2e tests.

**Consequence:** Affects developer experience, CI speed, and what kinds of bugs are caught.

---

### Decision 3: What to Test at Each Level

**Context:** Concrete test cases for THIS project, not generic advice. Depends on pyramid split (Decision 1) and framework selection (Decision 2).

Map the requirements' "Required Test Types" table to specific components and flows:

| Level | What to Test | What NOT to Test | Example |
|-------|-------------|-----------------|---------|
| **Unit** | Pure business logic, calculations, validation rules, transformations | Database queries, HTTP calls, file I/O | `calculateTax(price, region)` returns correct amount |
| **Integration** | API endpoints with real DB, service interactions, auth/authz flows | UI rendering, visual layout, edge cases covered by unit tests | `POST /orders` creates order in DB and returns 201 |
| **E2E** | Critical user journeys, cross-page flows, auth flows | Every UI permutation, edge cases already covered by unit tests | User can sign up, create order, see it in dashboard |
| **Model Eval** (ML only) | Accuracy on test set, regression on golden examples, bias metrics | Unit logic, UI flows | Model achieves > 85% accuracy on held-out test set |

**For each test type, define:**

| Test Type | What to Test | Example for THIS Project | Pass Criteria |
|-----------|-------------|------------------------|---------------|
| Unit | [specific function] | [concrete example] | [expected behavior] |
| Integration | [specific flow] | [concrete example] | [expected outcome] |
| E2E | [specific journey] | [concrete example] | [user can complete X] |

**Consequence:** Defines the scope of each test layer and prevents both gaps and redundancy.

---

### Decision 4: Integration Test Strategy

**Context:** How integration tests interact with external dependencies. Depends on what to test (Decision 3) and infrastructure constraints.

**Options:**

| | Option A: Real Services (TestContainers, Docker Compose) | Option B: Mocks / Stubs | Option C: Contract Testing (Pact) | Option D (local/cheap): In-Memory Fakes |
|---|---------|---------|---------|---------|
| What | Spin up real databases, caches, queues in containers | Replace external services with in-memory fakes | Define and verify API contracts between services | In-memory implementations (SQLite for DB, fake SMTP) |
| Best for | High confidence, testing real behavior | Fast tests, no infrastructure needed | Microservices with many service-to-service calls | Prototypes, fast feedback, no Docker needed |
| Trade-off | Slower, needs Docker, flaky if not managed | Mocks can drift from reality, false confidence | Contract maintenance overhead, learning curve | May not match production behavior |
| Cost | CI compute cost (container overhead) | Free | Free (Pact is open source) | Free |
| SOLID/DRY check | ✅ Tests real behavior | ⚠️ Risk of mock drift | ✅ Contracts as source of truth | ✅ Simple, but watch for behavior drift |

**Rule of thumb:** Use real services for things you own (your database, your cache). Mock things you don't own (third-party APIs, payment processors).

**Consequence:** Affects CI infrastructure, test speed, and confidence level.

---

### Decision 5: Regression Strategy

**Context:** How to prevent bugs from recurring and what runs when. Depends on pyramid split (Decision 1) and CI pipeline (Decision 7).

**Options:**

| | Option A: Everything on Every PR | Option B: Tiered (Fast on PR, Full Nightly) | Option C: Risk-Based (Affected Tests on PR) |
|---|---------|---------|---------|
| What | All tests run on every pull request | Unit + critical integration on PR; full suite nightly | Detect which tests are affected by changes, run only those |
| Best for | Small test suites (< 10 min total) | Medium test suites (10-30 min total) | Large test suites (30+ min total) |
| Trade-off | Slow PRs if test suite is large | Bugs found nightly may block morning work | Complex test selection, may miss dependencies |
| Cost | CI compute for every PR | Split compute (PR = cheap, nightly = full) | Test selection tooling + CI compute |
| SOLID/DRY check | ✅ Comprehensive, simple | ✅ Balanced speed and coverage | ✅ Efficient, but complex |

**Non-negotiable:** Every bug gets a regression test before the fix. The test must fail before the fix and pass after.

**Must match requirements' "Regression Policy" if specified.**

**Consequence:** Affects developer velocity (how long PRs take to merge) and bug detection timing.

---

### Decision 6: Test Data Strategy

**Context:** How test data is created and managed. Depends on integration test strategy (Decision 4).

**Options:**

| | Option A: Fixtures (Static Data) | Option B: Factories (Dynamic Generation) | Option C: Builders (Fluent API) | Option D: Production Snapshots |
|---|---------|---------|---------|---------|
| What | Pre-defined JSON/YAML/SQL files loaded before tests | Functions that generate data with sensible defaults and overrides | Chainable builder pattern for complex objects | Anonymized copy of production data |
| Best for | Simple data shapes, few test scenarios | Medium-large test suites, many variations needed | Complex objects with many optional fields | Testing with realistic data distributions |
| Trade-off | Brittle when schema changes, hard to vary | Must maintain factory definitions | More code, but very readable tests | PII risk, staleness, size |
| Cost | Free | Free (factory libraries) | Free | Anonymization tooling cost |
| SOLID/DRY check | ⚠️ Duplication across test files | ✅ DRY — single definition, many variations | ✅ DRY + readable | ⚠️ Must sanitize carefully |

**For ML projects:**
- **Test datasets:** Curated datasets for evaluation, versioned alongside model
- **Golden sets:** Known-good inputs and expected outputs for regression
- **Evaluation benchmarks:** Standardized metrics and thresholds

**Rule:** Never use production data in tests without anonymization. Use factories as the default — they scale better than fixtures.

**Consequence:** Affects test readability, maintenance burden, and data privacy.

---

### Decision 7: CI Pipeline Design

**Context:** How tests are orchestrated in CI. Depends on all previous decisions. Must match requirements' "CI/CD Expectations" if specified.

**Options:**

| | Option A: Linear Pipeline | Option B: Parallel Pipeline | Option C: Staged with Gates |
|---|---------|---------|---------|
| What | Each stage runs after the previous completes | Independent stages run in parallel where possible | Stages with explicit pass/fail gates between them |
| Best for | Simple projects, small test suites (< 5 min) | Medium-large projects (faster total time) | Production deployments, compliance requirements |
| Trade-off | Slowest total time, but simplest to debug | Faster, but harder to debug failures across parallel jobs | Most control, but more configuration |
| Cost | Minimal CI compute | More parallel compute (shorter wall time) | Same compute, more configuration |
| SOLID/DRY check | ✅ Simple, sequential | ✅ Efficient | ✅ Clear quality gates |

**Pipeline stages (recommended order):**

| Stage | What Runs | Blocks Merge? | Typical Duration |
|-------|----------|--------------|-----------------|
| Lint | ESLint, Ruff, Clippy | Yes | < 1 min |
| Type Check | TypeScript, mypy, go vet | Yes | < 2 min |
| Unit Tests | All unit tests | Yes | < 5 min |
| Integration Tests | API + DB integration tests | Yes | < 10 min |
| E2E Tests | Critical user journeys | Configurable | < 15 min |
| Security Scan | Dependency audit, SAST | Yes | < 5 min |
| Build | Production build | Yes | < 5 min |

**Which stages block merge?** At minimum: lint, type check, and unit tests must pass. Integration and e2e can be informational on draft PRs but must pass on final PRs.

**Consequence:** Affects developer feedback loop, merge velocity, and CI costs.

---

## Decision Format Reference

Each decision above follows the standard format from the base SKILL.md. For guardrails (G-ARCH-1 through G-ARCH-4, G1-G9), see `shared/guardrails.md` — they are not duplicated here.
