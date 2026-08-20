---
role: production
sources: 5
synthesized_at: 2026-08-17T01:15:24.213442
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
This role covers running and verifying applications: E2E/browser testing, smoke tests, performance testing, bug reproduction, and health verification before/during test runs. Sources span five repos with mature test infrastructure: AppFlowy (Flutter+Rust), Cypress RWA (reference Cypress app), Mattermost (dual E2E frameworks), Playwright (self-testing framework), PostHog (polyglot monorepo).

## Patterns Found (ranked by frequency)

### 1. Page Object / Fixture Layering (5/5 repos)
- **Playwright repo**: fixture chain `baseTest → serverFixtures → browserTest → domainTest` (`tests/config/browserTest.ts`)
- **PostHog**: page models (`playwright/page-models/loginPage.ts`, `dashboardPage.ts`) + `workspace-test-base.ts` for per-test workspace isolation
- **Cypress RWA**: custom commands (`cy.login()`, `cy.database()`) in `cypress/support/commands.ts`
- **Mattermost**: Playwright page objects in `e2e-tests/playwright/lib/`
- **AppFlowy**: delegate pattern for handlers; integration test dir at `integration_test/`

### 2. Test Sharding / Parallelism Control (4/5 repos)
- **Mattermost**: `shard-split.js` + `run-shard-tests.sh`; shard logic itself unit-tested (`shard-split.test.js`); test cycle generation (`generate_test_cycle.js`)
- **Playwright repo**: per-suite configs (`tests/{library,stress,mcp,...}/playwright.config.ts`), each independently runnable
- **Cypress RWA**: unit tests forced sequential — `fileParallelism: false` "to avoid race conditions with shared database.json"
- **PostHog**: `common/storybook/test-sequencer.js` controls story test order

### 3. Server Readiness / Health Gating Before Tests (4/5 repos)
- **Mattermost**: `wait-for-system-start.sh` polls server health pre-suite
- **PostHog**: `bin/ci-wait-for-docker`, `bin/check_ducklake_up`, `bin/check_dagster_graphql_up`, `bin/check_hosts`
- **Cypress RWA**: `start-server-and-test` + `wait-on` packages
- **Playwright repo**: fixtures spawn local test server per suite

### 4. Known-Failure / Quarantine Tracking (3/5 repos)
- **PostHog**: quarantine configs (`playwright.quarantine.ts`, `jest.quarantine.ts`) with dedicated reporter — flaky tests moved, not deleted; CI passes while tracking
- **Playwright repo**: expectation files (`tests/bidi/expectations/`, `tests/webview/expectations/`) list known failures per browser/platform; `expectationReporter.ts` diffs actual vs expected
- **Mattermost**: cycle-based selective execution

### 5. Visual Regression via Committed Snapshots (3/5 repos)
- **Playwright repo**: per-spec `*-snapshots/` dirs; custom comparator (`tests/config/comparator.ts`) using SSIM + pixel diff
- **PostHog**: PNGs committed to `frontend/__snapshots__/`; `snapshots.yml` manifests control which are active; dark/light mode variants
- **Cypress RWA**: Percy (`@percy/cypress`), widths `[1280]`

### 6. Database Seeding/Reset for Test Isolation (3/5 repos)
- **Cypress RWA**: `cy.task("db:seed")` → HTTP POST to `/testData/seed`; also `predev` script copies seed file; DB query tasks (`filter:database`, `find:database`) via lodash
- **PostHog**: per-service Postgres DBs via init scripts (`docker/postgres-init-scripts/create-*-db.sh`)
- **Mattermost**: testcontainers config spins up own DB (`playwright.testcontainers-up.config.ts`)

### 7. Mock Servers vs Real Local Servers (split approach)
- **Real local server (no HTTP mocking lib)**: Playwright repo (`tests/config/testserver/` serving `tests/assets/`), Cypress RWA (tests hit real backend)
- **Mock external services**: Mattermost (`mock_file_server.js`, `mock_libre_translate.js`), PostHog (`playwright/utils/mockApi.ts` route interception), Cypress RWA (mock AWS exports for CI)

## How Problems Are Solved

**PROBLEM: Authentication in E2E tests**
- Cypress RWA: per-provider command files (`auth-provider-commands/`); config-time guard flags (`config.expose.auth0_configured = Boolean(...)`) let tests skip unconfigured providers; credentials via tasks that throw with clear message if env vars missing
- PostHog: login page model reused across specs; dedicated specs for 2FA, password reset, invite flows

**PROBLEM: Flaky test management**
- Cypress RWA: `retries: { runMode: 2 }` (retries in CI only, 0 interactive)
- PostHog: quarantine files + reporter
- Playwright repo: flakiness dashboard — CI results downloaded into DuckDB (`utils/test-results-db/`), tracked over time, correlated with GitHub

**PROBLEM: Performance testing**
- PostHog: perf specs isolated from functional specs (`sql-editor-typing-perf.spec.ts`); ASV benchmarks (`ee/benchmarks/`); bundle-size reports posted as PR comments
- Playwright repo: dedicated stress suite (`tests/stress/browsers.spec.ts`, `contexts.spec.ts`); `bundle-size.spec.ts` in installation tests
- Mattermost: migration perf script (`psql-migration-test.sh`); extreme-dimension image fixtures (`10000x1.png` + expected outputs) for edge-case processing

**PROBLEM: Smoke testing release artifacts**
- PostHog: `cli/scripts/smoke-release-artifact.sh` — post-build binary verification
- Playwright repo: installation tests actually `npm install` in temp dirs (`npmTest.ts` fixture); example projects (`examples/todomvc/`) as real smoke suites
- Mattermost: `wait-for-system-start.sh` as smoke gate

**PROBLEM: API-level testing (bypassing UI)**
- Cypress RWA: dedicated `cypress/tests/api/` specs hitting REST directly; context-object pattern for state between hooks
- Mattermost: `api4/` integration tests hitting real HTTP endpoints; `openApiSync` linter prevents API/spec drift
- PostHog: Node.js ingestion server tests separate from browser E2E (different granularity per failure mode)

**PROBLEM: Test reporting into CI**
- Mattermost: webhook-based reporting (`report.webhookgen.js`) — decoupled from specific CI
- Playwright repo: `postReportComment.js` posts summaries to GitHub PRs; custom reporters (markdown, parquet, CSV)
- PostHog: `frontend/bin/post-bundle-size-comment.mjs` etc.

## Architecture Decisions Seen

- **Dual E2E frameworks during migration** (Mattermost): Cypress (legacy, broad) + Playwright (new) coexist. Tradeoff: two runner setups, duplicate coverage to audit.
- **Self-contained vs pre-provisioned test env** (Mattermost testcontainers): local full-E2E without dedicated env; tradeoff is container startup latency and infra fidelity.
- **Self-testing with pinned stable version** (Playwright repo): test runner tests itself via pinned older version in `stable-test-runner/` — avoids bootstrap paradox.
- **File-based DB for tests** (Cypress RWA lowdb): zero external deps, HTTP-resettable, directly inspectable; forces sequential unit tests.
- **Build-variant awareness** (Mattermost): OSS vs Enterprise are different binaries — E2E must target correct variant; some paths 403/404 on OSS.
- **CRDT/local-first sync** (AppFlowy): offline→online transition adds test complexity; dedicated `event-integration-test` crate for FFI-layer flows.

## Testing Approaches

| Layer | Examples |
|---|---|
| E2E browser | Playwright (PostHog, Mattermost, Playwright repo), Cypress (RWA, Mattermost) |
| API/HTTP | Cypress API specs (RWA), Go api4 tests (Mattermost) |
| Component | `*.cy.tsx` (RWA), Storybook test-runner (PostHog) |
| Visual | SSIM diff (Playwright), Percy (RWA), committed PNGs (PostHog) |
| Stress/perf | dedicated stress suite (Playwright), perf specs + ASV (PostHog) |
| Install/smoke | temp-dir npm installs (Playwright), release artifact scripts (PostHog) |
| Coverage | Istanbul via `vite-plugin-istanbul`, aggregated at `/__coverage__`, Codecov (RWA); Playwright repo has no explicit coverage — breadth-of-specs instead |

Common conventions: `*.spec.ts` for E2E, one file per feature area, fixtures/page-models in dedicated dirs, `sample.env`/`dotenv` templates documenting required env vars.

## Deployment & Production
- Health polling before test runs is universal where servers exist (Mattermost, PostHog, RWA).
- Docker Compose defines dev/test environments (Mattermost, PostHog); separate compose files for integration tests (PostHog livestream).
- Flakiness monitored as a production concern: DuckDB results DB + dashboard (Playwright repo).
- Config diffing between environments: `diff-config.sh` (Mattermost).
- Error recovery signals: `context.mounted` checks and dedicated error pages (AppFlowy); tested root error boundary (PostHog).

## Open Questions (for reviewer)
1. **Mocking philosophy**: real local test servers (Playwright, RWA) vs route interception/mock services (PostHog, Mattermost) — pick a default for E2E vs component levels?
2. **Flaky test policy**: retries-in-CI (RWA), quarantine files + reporter (PostHog), or expectation lists per platform (Playwright)? These are mutually compatible but need a chosen primary.
3. **Coverage**: explicit instrumentation (RWA Istanbul) vs breadth-of-specs with no coverage tooling (Playwright repo)?
4. **Dual framework tolerance**: is a Cypress→Playwright migration state acceptable, or standardize on one?
5. **Test data**: HTTP-seedable file DB (RWA) vs per-service isolated DBs (PostHog) vs testcontainers (Mattermost) — depends on target app architecture.
6. **RWA note**: `config.expose` appears non-standard (standard Cypress field is `env`) — verify before adopting that pattern.
