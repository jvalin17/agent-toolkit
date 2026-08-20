---
role: backend
sources: 8
synthesized_at: 2026-08-17T00:33:00.317859
---

# Backend Knowledge Base

## Advisory Context
Backend engineering covers API design, server-side business logic, auth, caching, integrations, and data pipeline wiring. This knowledge synthesizes production patterns from Stripe, Netflix Zuul, FastAPI, NestJS, Hono, Cal.com, and Medusa — favoring explicit contracts, layered defense, and fail-safe middleware.

## Patterns (use these)

### 1. Dependency Injection (5/8 sources: NestJS, FastAPI, Cal.com, Medusa/awilix, Zuul/Guice)
Services receive dependencies via constructor/parameter injection, never import singletons.
```python
# FastAPI
async def get_user(db: Annotated[DB, Depends(get_db)]): ...
```
```ts
// NestJS: constructor injection; Medusa: awilix container
constructor(private readonly userRepo: UserRepository) {}
```

### 2. Middleware/Filter Chain with Central Error Handling (5/8: Hono, NestJS, FastAPI, Zuul, Stripe)
Onion model: auth pre-handler, logging post-handler. Errors bubble to ONE handler.
```ts
app.use(async (c, next) => {
  try { await next() }
  catch (e) {
    if (e instanceof HTTPException) throw e
    throw new HTTPException(500, { message: 'Unexpected error', cause: e })
  }
})
app.onError((err, c) => { /* single place for logging, Sentry */ })
```
Explicit phase separation (Zuul): inbound filters mutate request, outbound mutate response — never mix.

### 3. Adapter/Provider Pattern for Swappable Infrastructure (4/8: Hono, NestJS, Medusa, Cal.com)
Abstract platform/vendor behind interfaces; select implementation at config time.
```
cache-inmemory / cache-redis — same interface
platform-express / platform-fastify — swappable adapters
```

### 4. Thin Controllers + Repository + Service Layers (Cal.com, Medusa)
Handlers validate input → call service → return DTO. Business logic never calls ORM directly; data shapes transformed at boundaries (Zod-validated DTOs, never raw DB models).

### 5. Validator-Driven Contracts (Medusa, Cal.com, FastAPI)
Validators are the single source of truth; types/schemas generated from them. Always declare `response_model` / output schemas — never return raw dicts (prevents field leakage).

### 6. Request-Scoped Explicit Context (Hono `Context`, Zuul `SessionContext`)
State lives ON the request object, never in ThreadLocal/ambient globals. Type it:
```ts
const app = new Hono<{ Bindings: Bindings; Variables: { user: User } }>()
```

### 7. Layered Rate Limiting (Stripe)
Token bucket per user (allows bursts) + concurrent request limiter + fleet load shedder + worker shedder. Rate limiters are *user-attributed*; load shedders are *system-attributed* — design separately. Classify traffic priority (critical POSTs > GETs > test mode) before shedding. Dark-launch every limiter: observe → tune → enforce. Kill switches via feature flags.

### 8. Saga/Workflow Orchestration (Medusa, microservices)
Multi-step operations (place order → reserve inventory → capture payment) as compensatable steps, not one transaction across services.

### 9. Lifespan Resource Management (FastAPI)
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await connect_db()
    yield
    await app.state.db.disconnect()
```

## Anti-Patterns + Fixes

### 1. Blocking the event loop / heavy work in-process (Zuul, FastAPI)
Blocking I/O or CPU work in async handlers starves ALL connections. In-process background tasks have no retry/queue/failure handling.
```python
# BAD
background_tasks.add_task(send_10k_emails, list)
# GOOD — real queue
await redis.enqueue_job("send_email_job", email)
```
Rule: any I/O-capable method must return a Promise/Future/Observable.

### 2. Swallowing errors in middleware (Hono, Zuul)
Catching and returning a plain response bypasses centralized error handling/monitoring.
```java
// BAD: catch (Exception e) { log.error("failed"); }  // request proceeds corrupted
// GOOD: throw new ZuulFilterException("MyFilter failed", e);  // routed to error handler
```

### 3. Non-actionable error responses (Stripe, FastAPI)
```python
# BAD: raise HTTPException(status_code=400)
# GOOD:
raise HTTPException(401, detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"})
# 429s MUST include Retry-After + X-RateLimit-* headers + structured body
```

### 4. Over-fetching / raw model returns (FastAPI, Medusa, Cal.com — 3 sources)
Returning ORM models leaks fields; `include`/`*` selectors over-fetch.
```python
class UserOut(BaseModel):  # explicit output contract
    id: int
    name: str
@app.get("/users/{id}", response_model=UserOut)
```
Prisma: `select` over `include`. Centralize field lists as named constants, not inline magic strings.

### 5. Fail-closed middleware (Stripe)
Rate limiter/cache outage must not take down the API.
```python
try:
    result = await asyncio.wait_for(redis_check(user_id), timeout=0.005)
except (asyncio.TimeoutError, redis.RedisError):
    metrics.increment("rate_limiter.fail_open")
    return True  # allow through — availability > perfect enforcement
```

### 6. Fixed-window rate limiting (Stripe)
Allows 2× burst at window edges. Use token bucket with atomic Redis Lua script (see Bug 1).

### 7. Parsing user input without validation (Medusa)
```ts
// BAD: JSON.parse(queryParam)  // crashes on malformed input
// GOOD:
try {
  const result = dateFilterSchema.safeParse(JSON.parse(value))
  return result.success ? result.data : undefined
} catch { return undefined }
```

### 8. Unbounded lookups with magic limits (Medusa)
`limit: 1000` silently breaks at scale. Use server-side search with pagination (`q: query, limit: 50`).

### 9. Test-environment branches in production code (Cal.com)
`if (process.env.INTEGRATION_TEST_MODE)` in prod code = architectural smell.
```ts
import 'server-only'  // build-time guard instead
// or lazy-load: const dep = await import('./server-only-module')
```

### 10. Untyped ambient context (Hono, Zuul)
`c.env.MY_KV` without type binding = `any`, runtime failure. `ThreadLocal` in async = cross-request data leakage (auth leaks!). Always: typed generics + context bound to the request object.

### 11. Flapping load restoration (Stripe)
Shed at 90% utilization, restore at 60% — hysteresis gap plus cooldown:
```python
if time.time() - self.last_change < 120: return  # cooldown
if util > 0.90: self.shed_level += 1
elif util < 0.60: self.shed_level -= 1  # one level at a time
```

## Architecture Decisions

| Decision | Tradeoff |
|---|---|
| Centralized rate-limit state (Redis) vs local | Accurate across fleet, but must fail-open on outage |
| Two API surfaces (internal tRPC + public REST) | Type safety internally + stable external contract; cost: dual auth/middleware maintenance — need explicit versioning + deprecation headers |
| Modules as independent packages | Independent versioning; cost: cross-module type coordination (use link modules, never direct imports) |
| Async event loop vs thread-per-request | 10K+ concurrent connections on few threads; cost: harder debugging, connection pools must be sized >> thread count (5000, not 200) |
| Feature flags in DB vs env vars | Works self-hosted, no vendor; cost: must cache flag checks |
| Web-standard Request/Response vs framework-native | Runtime portability; cost: adapter shims per platform |
| Codegen types from validators vs manual | Client/server can't drift; cost: build step |

## Quality Checks
- [ ] No business logic in route handlers — services only
- [ ] All output goes through explicit response models/DTOs (no raw ORM models)
- [ ] All user input (body, query, URL params) schema-validated before use
- [ ] Errors propagate to centralized handler; no swallowed exceptions in middleware
- [ ] Error responses actionable: detail message, correct status, `Retry-After` on 429, `WWW-Authenticate` on 401
- [ ] No blocking I/O in async handlers; heavy work goes to a real queue
- [ ] Middleware fail-open with timeout on external dependencies (Redis, auth service)
- [ ] Request-scoped state on context object, never ThreadLocal/module globals
- [
