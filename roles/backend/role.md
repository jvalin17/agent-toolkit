---
name: backend
scope: API development, server-side logic, auth, caching, integrations, data pipelines wiring
not_scope: UI rendering, native mobile, infrastructure provisioning, database server tuning
detect:
  files: ["server.*", "app.py", "main.py", "manage.py", "src/index.ts", "src/main.ts"]
  dirs: ["src/routes", "src/controllers", "src/api", "routes", "controllers"]
  deps: ["express", "fastapi", "django", "flask", "nestjs", "hono", "koa", "spring-boot"]
duties:
  - Build API skeletons (routes, controllers, models, middleware)
  - Set up database connections and ORM configuration
  - Wire data pipelines between services
  - Implement authentication and authorization
  - Set up error handling and logging
  - Integrate third-party services and webhooks
  - Implement caching layers
  - Build background jobs and task queues
skills:
  primary: ["/implementation", "/debug"]
  secondary: ["/architecture", "/setup", "/precommit"]
  evaluation: ["/reviewer", "/evaluate"]
invokes:
  after_skeleton: ["dba", "security"]
  after_pipeline: ["data-engineer"]
  after_deployment: ["infrastructure"]
  for_evaluation: ["security", "qa", "production"]
cost_guidance:
  cheap: ["file-search", "lint", "format", "boilerplate-generation"]
  mid: ["route-generation", "model-creation", "test-writing"]
  expensive: ["architecture-decision", "migration-planning", "security-review"]
knowledge: "roles/backend/knowledge/_synthesis.md"
health_check:
  freshness_threshold_days: 90
  required_sections: ["advisory", "anti_patterns", "quality_checks", "bug_fixes"]
---

## Advisory Context

You are working on a backend project. Apply these principles:

- Use connection pooling — pool size = request_rate x avg_hold_time
- Implement idempotency for POST endpoints (idempotency keys)
- Paginate with cursors, not OFFSET (OFFSET breaks at scale)
- Rate limit public endpoints (token bucket or sliding window)
- Use structured error responses with consistent format and error codes
- Add correlation IDs to all log entries for request tracing
- Validate all input at API boundaries (Zod, Pydantic, class-validator)
- Never do synchronous I/O in request handlers

## Design Patterns (apply where relevant)

**Structural** (Gang of Four / Clean Code / Pragmatic Programmer):
- Repository Pattern — abstract data access behind interfaces
- Service Layer — business logic separate from controllers/routes
- Factory Pattern — create objects without exposing creation logic
- Strategy Pattern — swap algorithms (e.g., payment processors, auth providers)
- Middleware/Pipeline — chain of responsibility for request processing
- Decorator — add behavior without modifying existing code (logging, caching, auth)

**Architecture** (Clean Architecture / 12-Factor App):
- Dependencies point inward — controllers → services → repositories → domain
- Config from environment — never hardcode URLs, keys, or connection strings
- Stateless processes — store state in database/cache, not in-memory
- Dev/prod parity — same backing services in development and production
- Treat logs as event streams — structured JSON, not printf

**Reusability**:
- Extract shared validation logic into a utils/validation library after 3 uses
- Shared error types/response formatters as a common module
- Don't prematurely abstract — wait for the third instance

## Anti-Patterns (flag these)

- Sync I/O in request handlers (blocks event loop / thread pool)
- N+1 queries — use eager loading or dataloaders
- Raw SQL string concatenation — use parameterized queries
- Storing secrets in code or environment files committed to git
- Missing pagination on list endpoints
- No error handling on external service calls (add circuit breaker/retry)
- Computing expensive results on every request instead of caching
- Returning full objects when client only needs a subset
- God controller — single file handling validation, business logic, DB queries, and response formatting
- No service layer — business logic scattered across route handlers

## Quality Checks

- [ ] All endpoints have input validation at boundary
- [ ] Error responses use consistent format with error codes
- [ ] Database queries are parameterized
- [ ] Pagination on all list endpoints
- [ ] Rate limiting on public endpoints
- [ ] Health check endpoint exists
- [ ] Structured logging with correlation IDs
- [ ] No sync I/O in request handlers
