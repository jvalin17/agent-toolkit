# Backend Implementation

Implement business logic, data models, core algorithms, API endpoint logic, database operations, and background tasks using TDD.

## Inputs

Read from upstream docs:
- **Requirements doc:** feature descriptions, data models, business rules, API specs, priority levels
- **Architecture doc:** tech stack, component diagram, data flow, API design, database schema, service interactions
- **Testing architecture:** test pyramid, framework selection, integration strategy

Follow upstream decisions. Do not re-decide tech stack, framework, or patterns.

## What Backend Mode Implements

- API endpoints (REST, GraphQL, gRPC)
- Business logic and core algorithms
- Data models and database operations
- Background tasks and job processing
- Service-to-service communication

## TDD Patterns by Language

| Language | Test Framework | Test Pattern |
|----------|---------------|-------------|
| Python | pytest | `def test_<what>_<scenario>_<expected>():` with Arrange/Act/Assert |
| Java | JUnit 5 | `@Test void should<What>_when<Scenario>()` with Given/When/Then |
| Go | testing | `func Test<What>_<Scenario>(t *testing.T)` with table-driven tests |
| Rust | built-in | `#[test] fn test_<what>_<scenario>()` |
| C# | xUnit/NUnit | `[Fact] public void Should<What>_When<Scenario>()` |
| JavaScript | Jest/vitest | `test('<what> <scenario>', () => {})` |

For language-specific coding standards, see `references/coding-standards-index.md`.

## What to Test at Each Level

- **Unit:** Individual functions/methods, business logic, data transforms
- **Integration:** API endpoints end-to-end, database operations, service interactions
- **Contract:** Request/response shapes match API spec

## Backend Anti-Patterns (from real usage — these cause silent failures)

1. **Never mix async HTTP in sync endpoints.** If your endpoint is `def` (not `async def`), use sync HTTP clients (`httpx.get()`, `requests.get()`). Using `async with httpx.AsyncClient()` in a sync endpoint running in a thread pool creates event loop conflicts that **fail silently** — returns empty results with no error.
2. **Never combine ThreadPoolExecutor + asyncio.run.** This pattern appears to work in unit tests but fails silently in request context. If you need async in sync code, refactor the endpoint to `async def` or use sync calls.
3. **Auto-create .env file when detecting `os.environ.get()`.** If the code reads env vars, ensure `.env.example` exists with all required keys. API keys set in shell are lost on restart — `.env` loaded by dotenv is the correct pattern.
4. **Pre-load API keys from .env for developer.** If `.env` has keys, they should work immediately without manual configuration in a Settings UI. Seed from env on startup.
5. **Config changes must not require restart.** If settings are stored in DB, lazy-load per request or reload services when settings change. Don't cache config at startup.
6. **Document dependency constraints.** When a project has 10+ dependencies, create DECISIONS.md listing each package, version, size, and why it's there.
7. **Live integration tests with separate marker.** Every external API integration needs at least 1 live test (e.g., `@pytest.mark.live`) that hits the real API. Don't mix with unit tests — run separately.

## Checklist Per Block

- [ ] Happy path tested
- [ ] Edge cases tested (empty input, boundary values, null/undefined)
- [ ] Error cases tested (invalid input, missing data, unauthorized)
- [ ] Database operations tested (CRUD, constraints, concurrent access)
- [ ] No async/sync mixing in endpoints
- [ ] .env.example updated with any new env vars
- [ ] Follows project's established patterns

## TDD Cycle

For each piece of business logic in the slab:

1. **TEST FIRST** — Write a failing test that describes the expected behavior
2. **RUN TEST** — Confirm it fails (red)
3. **IMPLEMENT** — Write the minimum code to make the test pass
4. **RUN TEST** — Confirm it passes (green)
5. **REFACTOR** — Clean up without changing behavior
6. **RUN TEST** — Confirm still green

One function per TDD cycle. Do not write 500 lines then test.

For guardrails and core principles, see the main `SKILL.md`.
