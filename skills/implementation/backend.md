# Backend Implementation
Keywords: API, business logic, data models, database, endpoints, background tasks

Implement business logic, data models, API endpoints, database operations, and background tasks using TDD.

## Inputs

Read from upstream docs (requirements, architecture, testing architecture). Follow upstream decisions — do not re-decide tech stack, framework, or patterns.

## Backend Anti-Patterns (from real usage — these cause silent failures)

1. **Never mix async HTTP in sync endpoints.** If your endpoint is `def` (not `async def`), use sync HTTP clients (`httpx.get()`, `requests.get()`). Using `async with httpx.AsyncClient()` in a sync endpoint running in a thread pool creates event loop conflicts that **fail silently** — returns empty results with no error.
2. **Never combine ThreadPoolExecutor + asyncio.run.** This pattern appears to work in unit tests but fails silently in request context. If you need async in sync code, refactor the endpoint to `async def` or use sync calls.
3. **Auto-create .env file when detecting `os.environ.get()`.** If the code reads env vars, ensure `.env.example` exists with all required keys. API keys set in shell are lost on restart — `.env` loaded by dotenv is the correct pattern.
4. **Pre-load API keys from .env for developer.** If `.env` has keys, they should work immediately without manual configuration in a Settings UI. Seed from env on startup.
5. **Config changes must not require restart.** If settings are stored in DB, lazy-load per request or reload services when settings change. Don't cache config at startup.
6. **Document dependency constraints.** When a project has 10+ dependencies, create DECISIONS.md listing each package, version, size, and why it's there.
7. **Live integration tests with separate marker.** Every external API integration needs at least 1 live test (e.g., `@pytest.mark.live`) that hits the real API. Don't mix with unit tests — run separately.

## Checklist Per Block

- [ ] No async/sync mixing in endpoints
- [ ] .env.example updated with any new env vars
- [ ] Follows project's established patterns

For language-specific coding standards, see `references/coding-standards-index.md`.

For guardrails and core principles, see the main `SKILL.md`.
