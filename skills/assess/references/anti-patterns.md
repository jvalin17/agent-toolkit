# Anti-Patterns — Known Problems by Category

> Technical debt signals. Each has a severity and fix approach.

## Always Fix (any scale)

### Database
- **N+1 queries** — loop fetching rows one at a time. Fix: batch query, eager loading, DataLoader.
- **Hardcoded connection strings** — credentials in source code. Fix: environment variables.
- **No migrations** — schema changes applied manually. Fix: migration tool (Alembic, Prisma, Flyway).

### API
- **Inconsistent error handling** — mix of formats, status codes across endpoints. Fix: standard error envelope.
- **No input validation** — trusting client data. Fix: validate at server boundary.

### Frontend
- **No ErrorBoundary** — one component crash blanks entire screen. Fix: wrap routes in ErrorBoundary.
- **Promise.all for independent data** — one failure blanks all data. Fix: load each source independently.
- **Silent catches** — `catch {}` swallows errors. Fix: show toast.error or user-visible message.
- **Async/sync mixing** — async HTTP in sync endpoints fails silently. Fix: match async/sync consistently.

### Code
- **God classes** — files >500 lines doing everything. Fix: split by responsibility.
- **Circular dependencies** — A imports B imports A. Fix: extract shared interface.
- **Hardcoded secrets** — passwords/keys in code. Fix: environment variables or secret manager.

### Testing
- **Tests mock what they test** — testing the mock, not the code. Fix: mock dependencies, not the subject.
- **No integration tests** — units pass but system breaks when assembled. Fix: at least 1 e2e test.
- **Sloppy assertions** — assertTrue(True), toBeTruthy(). Fix: specific value assertions.

## Scale-Dependent (check current numbers before flagging)

### Database (>10K rows)
- **Missing indexes** on filtered/joined columns. Verify with EXPLAIN ANALYZE.
- **No connection pooling** for server apps. Each connection = ~1.3MB.

### API (>100 QPS)
- **No caching** on frequently-read, rarely-written data.
- **No rate limiting** when external consumers exist.

### Frontend (any app with users)
- **Prop drilling >3 levels** — signal for context or state management.
- **Components >200 lines** — split into orchestrator + presentational.
- **No empty states** — blank screen when data is missing.
- **Dynamic text without overflow** — long strings break layout.

### Architecture
- **Monolith pain** at >8-10 engineers — consider modular monolith or extraction.
- **SQLite limits** at concurrent writes or multi-server — consider PostgreSQL.
- **No observability** in production — at minimum, structured logging + error tracking.

## AI/ML Specific

- **Full corpus in every prompt** — wasteful if most is irrelevant. Context engineering can cut 50-90%.
- **No provider abstraction** — locked to one LLM vendor with no swap path.
- **No token budget** — uncontrolled API costs. Fix: budget check in provider wrapper.
- **No offline fallback** — app is useless without internet. Fix: three-mode design (no-LLM, offline, online).
- **RAG when context stuffing works** — added complexity for no benefit under 50 pages.
