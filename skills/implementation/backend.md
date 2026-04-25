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

## Checklist Per Block

- [ ] Happy path tested
- [ ] Edge cases tested (empty input, boundary values, null/undefined)
- [ ] Error cases tested (invalid input, missing data, unauthorized)
- [ ] Database operations tested (CRUD, constraints, concurrent access)
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
