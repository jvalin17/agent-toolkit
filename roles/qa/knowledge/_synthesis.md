---
role: qa
sources: 5
synthesized_at: 2026-08-17T02:01:34.323788
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
QA knowledge synthesized from 5 testing-focused OSS projects: an E2E reference app (cypress-realworld-app), two test frameworks (Playwright, pytest), a mutation-testing tool (StrykerJS), and a component-testing library (react-testing-library). Covers test layering, fixtures, isolation, seeding, snapshots, flakiness handling, CI gates, and coverage strategy.

## Patterns Found (ranked by frequency across repos)

**1. Fixture / Dependency-Injection for Test Setup** (playwright, pytest, cypress-rwa)
Tests declare needs; framework provides isolated resources.
```typescript
// playwright: tests/config/browserTest.ts — compose via test.extend()
// pytest: fixture manager resolves scoped fixtures; pytester spawns real subprocess runs
// cypress-rwa: custom commands in cypress/support/commands.ts — cy.login(), cy.task("db:seed")
```

**2. Snapshot/Baseline Testing** (playwright, stryker-js, RTL)
- Playwright: image baselines in `<spec>.spec.ts-snapshots/` adjacent to specs, per-platform dirs, `--update-snapshots` flag; also ARIA snapshots (`ariaSnapshot.ts`) as accessibility-tree alternative to visual diffs.
- StrykerJS: `chai-jest-snapshot` for E2E output; update via `CHAI_JEST_SNAPSHOT_UPDATE_ALL=true pnpm run e2e`.
- RTL: Jest snapshots in `src/__tests__/__snapshots__/`; `npm run test:update`.
- cypress-rwa: Percy for visual regression (`@percy/cypress`, 1280px width).

**3. Self-Hosting / Dogfooding** (playwright, pytest, stryker-js)
- pytest: `pytester` fixture spawns subprocess pytest runs; asserts on stdout/exit codes.
- Playwright: `tests/playwright-test/` uses a pinned `stable-test-runner` to avoid bootstrap circularity.
- StrykerJS: each package has `stryker.conf.js` — mutation-tests itself; score badge on README.

**4. Scenario-per-Directory E2E Organization** (stryker-js, pytest, playwright)
```
e2e/test/exit-prematurely-dry-run-fails/   # stryker: named after behavior under test
testing/example_scripts/collect/...        # pytest: real files as pytester inputs, excluded via norecursedirs
tests/{library,installation,stress,bidi}/  # playwright: suite per domain, each with own playwright.config.ts
```

**5. Test Layer Separation** (all 5) — see Testing Approaches below.

**6. Auto-cleanup with escape hatch** (RTL)
```js
if (typeof afterEach === 'function') { afterEach(() => cleanup()) }
// Opt out: RTL_SKIP_AUTO_CLEANUP env var, or import from pure.js
```

**7. Shared test context object** (cypress-rwa)
```ts
type TestBankTransferCtx = { authenticatedUser?: User };
let ctx: TestBankTransferCtx = {}; // passes data between before/it blocks
```

## How Problems Are Solved

**PROBLEM: Test isolation / state leakage**
- playwright: fresh `BrowserContext` per test via fixtures (default, no shared state).
- RTL: auto-cleanup unmounts DOM after each test.
- pytest: subprocess isolation via pytester; `monkeypatch` fixture for env/attrs.
- cypress-rwa: DB re-seed via task before suites:
```ts
async "db:seed"() { const { data } = await axios.post(`${testDataApiEndpoint}/seed`); return data; }
```
- Constraint acknowledged: shared JSON DB forces sequential runs — `fileParallelism: false // #1666 race conditions with shared database.json`.

**PROBLEM: Test data**
- cypress-rwa: three-tier — static fixtures (`cypress/fixtures/`), faker-generated seed (`scripts/generateSeedData.ts` → `database-seed.json`), `empty-seed.json` for empty-state scenarios. Tests query live DB for assertions (`filter:database` / `find:database` tasks with lodash) rather than trusting fixtures.
- playwright: `tests/assets/` static assets served by test-server fixture.
- stryker-js: `testResources/` fixture projects per package, pre-instrumented via `tasks/instrument-test-resources.js`.
- pytest: `testing/example_scripts/` real `.py` files as inputs (chosen over inline strings for lint/highlighting).

**PROBLEM: Flakiness**
- cypress-rwa: `retries: { runMode: 2 }` global CI retry.
- playwright: dedicated flakiness dashboard (`utils/flakiness-dashboard/`, Azure Functions), Parquet reporter + DuckDB-backed test-results history (`utils/test-results-db/`).
- stryker-js: `forbidOnly: Boolean(process.env.CI)` blocks `.only()` in CI.
- pytest: `slow` marker; conftest reorders slow tests to end.

**PROBLEM: Known failures without blocking CI**
- playwright: checked-in expectation files (`tests/bidi/expectations/`, `tests/webview/expectations/`) track conformance over time.

**PROBLEM: Unexpected console/warning noise**
- RTL: global console interception fails tests on unexpected `console.error/warn` (`tests/failOnUnexpectedConsoleCalls.js`) with allowlist; custom `toWarnDev` matcher.
- pytest: `filterwarnings = ['error', ...]` — warnings are errors by default with explicit exemptions.

**PROBLEM: Auth in E2E**
- cypress-rwa: `cy.login()` bypasses UI for local auth; per-provider command sets in `cypress/support/auth-provider-commands/`; suites gated on `config.expose.[provider]_configured`; missing credentials throw explicitly in tasks.

**PROBLEM: Network mocking**
- playwright: `page.route()`, HAR record/replay, proxy fixtures, clock manipulation, CDP sensor mocks.
- RTL: manual module mock (`src/__mocks__/axios.js`) — no auto-mocking.
- cypress-rwa: deliberately none — tests run against live backend (see Architecture Decisions).

**PROBLEM: Coverage across environments**
- pytest: branch coverage + subprocess patching (`patch = ["subprocess"]`) so child processes count; `parallel = true` for xdist.
- RTL: per-file thresholds below 100% by design; Codecov merges React 18 + 19 matrix jobs.
- cypress-rwa: frontend via `vite-plugin-istanbul`, backend via `nyc`, collected at `/__coverage__`, merged by `@cypress/code-coverage`.
- stryker-js: `c8` (V8-native) plus mutation score as suite-quality metric.

## Architecture Decisions Seen

**Real backend vs mocked API** — cypress-rwa runs all tests against live Express + lowdb JSON DB. Tradeoff: catches real backend bugs, zero DB setup; forces sequential execution, slower tests. Playwright/RTL take the opposite approach (controlled test servers / mocks).

**Subprocess E2E vs in-process** — pytest chose subprocess (pytester): real user-facing behavior, no state leakage; cost is speed, debuggability, coverage complexity.

**Monorepo per-package test config** — playwright (npm workspaces) and stryker-js (lerna + pnpm) both give each package/suite its own config (`playwright.config.ts` per dir; `.mocharc.cjs`, `stryker.conf.js`, `tsconfig.src.json`/`tsconfig.test.json` per package).

**Coverage split across CI matrix** — RTL deliberately sets sub-100% per-job thresholds because React 18/19 paths can't both run in one job; Codecov aggregates.

**Pure vs side-effect entry points** — RTL's `index.js` vs `pure.js`. QA risk noted: importing `pure` skips auto-cleanup → cross-test pollution.

**Version compatibility testing** — stryker-js keeps `jest-old-version/`, `cucumber-old-version/` E2E scenarios; RTL uses conditional types + build matrix for React 18/19; pytest uses conditional backport deps across Python 3.10–3.15.

## Testing Approaches

**Layering (consistent across repos):**
| Layer | cypress-rwa | playwright | pytest | stryker-js |
|---|---|---|---|---|
| Unit | Vitest, `src/__tests__/` | `tests/library/unit/` | testing/*.py | Mocha per package |
| Component/Integration | Cypress CT, co-located `*.cy.tsx` | `tests/page/`, `tests/library/` | pytester in-process | package `test/` |
| API | `cypress/tests/api/` (live backend) | — | — | — |
| E2E | `cypress/tests/ui/` | `tests/playwright-test/` (self) | pytester subprocess | `e2e/test/<scenario>/` |
| Specialized | mobile viewport scripts, Percy visual | stress, installation smoke, conformance, MCP | freeze/PyInstaller, plugin compat, doctests | perf package, mutation dogfood |

**Naming conventions:**
- cypress-rwa: `*.spec.ts` (E2E), `*.cy.tsx` (component, co-located)
- playwright: `<subject>-<verb>.spec.ts`, `<scope>Fixtures.ts`
- pytest: `test_*.py`, `Test`/`Acceptance` class prefixes
- stryker-js: kebab-case scenario dirs describing behavior (`disable-bail`, `hit-limit`)

**Semantic locators** (playwright): `page.getByRole('link', { name: 'Get started' })` over raw selectors.

**Type-level testing** (RTL): compile-time `expectType<Expected, Actual>` in `types/test.tsx`, part of typecheck script.

**Property-based testing** (pytest): hypothesis for `approx()` and similar.

## Deployment & Production
- CI: GitHub Actions in all repos; `start-server-and-test` (cypress-rwa) waits for servers; stryker-js `e2e:ci` uses `--frozen-lockfile`.
- Cypress Cloud dashboard + Codecov (cypress-rwa); Codecov also in pytest, RTL.
- Playwright: Docker images with seccomp profiles for browser sandboxing; PR-comment reporter (`postReportComment.js`); AVD scripts for Android.
- Release automation: semantic-release (RTL), lerna version + GH token (stryker-js), setuptools-scm + release scripts (pytest).
- Traceability: pytest maps every fix to `changelog/<issue>.bugfix.rst` (towncrier).

## Open Questions (for reviewer)
1. **Real backend vs mocked network in E2E** — cypress-
