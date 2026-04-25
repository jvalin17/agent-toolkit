# Testing Frameworks Reference

> **Our synthesis.** Framework recommendations based on current ecosystem (2026).
> Check official docs for latest versions and features.
> Last verified: 2026-04-24

## Sources
- [pytest documentation](https://docs.pytest.org/)
- [vitest documentation](https://vitest.dev/)
- [JUnit 5 User Guide](https://junit.org/junit5/docs/current/user-guide/)
- [Go testing package](https://pkg.go.dev/testing)
- [Testing Library](https://testing-library.com/)
- [Kent C. Dodds — Testing Trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications)

---

## By Language

### Python
| Purpose | Framework | Install |
|---------|-----------|---------|
| Unit / Integration | **pytest** | `uv add --dev pytest pytest-asyncio` |
| Mocking | **unittest.mock** (stdlib) | built-in |
| HTTP testing | **httpx** (FastAPI TestClient) | `uv add --dev httpx` |
| Coverage | **pytest-cov** | `uv add --dev pytest-cov` |
| Data validation | **hypothesis** | `uv add --dev hypothesis` |
| ML model testing | **pytest** + custom fixtures | — |

**Naming:** `test_<what>_<scenario>_<expected>()`
**Structure:** Arrange → Act → Assert

### TypeScript / JavaScript
| Purpose | Framework | Install |
|---------|-----------|---------|
| Unit / Integration | **vitest** | `npm i -D vitest` |
| Component testing | **@testing-library/react** (or /vue, /svelte) | `npm i -D @testing-library/react` |
| Mocking | **vi.fn(), vi.mock()** (vitest built-in) | — |
| E2E | **Playwright** | `npm i -D @playwright/test` |
| Coverage | **@vitest/coverage-v8** | `npm i -D @vitest/coverage-v8` |

**Naming:** `test('should <what> when <scenario>', () => {})`
**Structure:** Render → Query → Assert → Interact

### Java
| Purpose | Framework | Install |
|---------|-----------|---------|
| Unit / Integration | **JUnit 5** | Maven/Gradle dependency |
| Mocking | **Mockito** | Maven/Gradle dependency |
| API testing | **MockMvc** (Spring) or **REST Assured** | — |
| Coverage | **JaCoCo** | Maven/Gradle plugin |

**Naming:** `@Test void should<What>_when<Scenario>()`
**Structure:** Given → When → Then

### Go
| Purpose | Framework | Install |
|---------|-----------|---------|
| Unit / Integration | **testing** (stdlib) | built-in |
| Assertions | **testify** | `go get github.com/stretchr/testify` |
| HTTP testing | **httptest** (stdlib) | built-in |
| Coverage | `go test -cover` | built-in |

**Naming:** `func Test<What>_<Scenario>(t *testing.T)`
**Structure:** Table-driven tests with subtests

### Rust
| Purpose | Framework | Install |
|---------|-----------|---------|
| Unit / Integration | built-in `#[test]` | — |
| Assertions | built-in `assert!`, `assert_eq!` | — |
| Async testing | **tokio::test** | `tokio` with `test` feature |
| Coverage | **cargo-tarpaulin** | `cargo install cargo-tarpaulin` |

**Naming:** `#[test] fn test_<what>_<scenario>()`

---

## Test Pyramid Split (by project type)

| Project Type | Unit | Integration | E2E |
|-------------|------|------------|-----|
| API-heavy backend | 60% | 30% | 10% |
| UI-heavy frontend | 50% | 20% | 30% |
| Full-stack app | 55% | 25% | 20% |
| ML pipeline | 40% | 40% | 20% |
| CLI tool | 70% | 20% | 10% |
