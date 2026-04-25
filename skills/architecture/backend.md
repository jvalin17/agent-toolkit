# Backend Architecture

Decisions for the backend layer: data, APIs, code structure, data flow, and extensibility. These areas are always relevant regardless of project type.

## Inputs

Read `requirements/<name>.md` and extract:
- **Functional requirements** — what the system does (CRUD, real-time, batch processing)
- **Non-functional requirements** — scale targets, latency, availability
- **Constraints** — hosting, budget, team size, existing tech stack
- **Integration requirements** — third-party services, legacy systems

Also read the Quick Architecture from `architecture/<name>.md` for the chosen architecture pattern, tech stack, and API approach.

---

## Part 1: Data Architecture

6 decisions covering how data is stored, accessed, and evolved.

### Decision 1: Database Type

**Context:** The foundational data decision. Everything else depends on this.

**Options:**

| | Option A: SQL (PostgreSQL/MySQL) | Option B: NoSQL (MongoDB/DynamoDB) | Option C: Both (polyglot persistence) | Option D (local/cheap): SQLite |
|---|---------|---------|---------|---------|
| What | Relational database with structured schemas and ACID transactions | Document/key-value store with flexible schemas | Different databases for different data types | File-based SQL database, zero setup |
| Best for | Complex queries, relationships, transactions, reporting | Unstructured/semi-structured data, high write throughput, flexible schema | Large systems with varied data access patterns | Prototypes, single-server apps, embedded systems, surprisingly high read loads |
| Trade-off | Schema changes require migrations, horizontal scaling is harder | No joins (or expensive joins), eventual consistency by default | Operational complexity — multiple systems to manage | Single-writer, no network access, limited concurrent writes |
| Cost | Free (PostgreSQL) to moderate (managed services) | Free tier available (MongoDB Atlas, DynamoDB) | Highest — multiple systems | Free, zero infrastructure |
| SOLID/DRY check | ✅ Strong contracts via schema | ⚠️ Schema flexibility can hide inconsistency | ⚠️ Violates KISS unless justified | ✅ Simplest possible choice |

**CAP theorem:** "You can have 2 of 3: Consistency, Availability, Partition tolerance. SQL databases favor CP (consistent under network partitions). NoSQL databases typically favor AP (available under partitions, eventually consistent)."

**Consequence:** Shapes schema design, caching strategy, and consistency model.

---

### Decision 2: Schema Design

**Context:** How data is structured. Depends on database type (Decision 1).

**Options:**

| | Option A: Fully Normalized (3NF+) | Option B: Denormalized | Option C: Hybrid |
|---|---------|---------|---------|
| What | Each fact stored once, relationships via foreign keys | Data duplicated for read performance | Normalize writes, denormalize reads (materialized views, CQRS) |
| Best for | Write-heavy apps, data integrity is critical | Read-heavy apps, simple queries, document databases | Apps with different read/write patterns |
| Trade-off | Complex joins for reads, but no data inconsistency | Data duplication, update anomalies | More complex but optimizes for both paths |
| Cost | Same | Same (more storage) | Higher engineering cost |
| SOLID/DRY check | ✅ DRY — no duplication | ⚠️ Violates DRY intentionally | ✅ Balanced — DRY for writes, optimized for reads |

**Consequence:** Affects query complexity, read/write performance, and migration difficulty.

---

### Decision 3: Read/Write Patterns

**Context:** Understanding the access pattern shapes replication and caching. Depends on schema design (Decision 2).

**Options:**

| | Option A: Read-Heavy | Option B: Write-Heavy | Option C: Mixed/Balanced |
|---|---------|---------|---------|
| What | Most operations are reads (10:1 or higher read:write ratio) | Most operations are writes (logging, event sourcing, IoT) | Roughly equal reads and writes |
| Best for | Content sites, dashboards, catalogs | Analytics ingestion, audit logs, real-time feeds | CRUD applications, collaborative tools |
| Optimization | Read replicas, caching layers, CDN | Write-optimized storage (append-only, batched writes), async processing | Standard database with connection pooling |
| Scaling approach | Add read replicas, cache aggressively | Shard by write key, use queue-based writes | Vertical scaling first, then shard |
| SOLID/DRY check | ✅ Clear separation of read path | ✅ Clear separation of write path | ✅ Simple unified path |

**Consequence:** Determines caching strategy and consistency model.

---

### Decision 4: Caching Strategy

**Context:** What to cache, where, and how to invalidate. Depends on read/write patterns (Decision 3).

**Options:**

| | Option A: Application-Level Cache | Option B: Distributed Cache (Redis/Memcached) | Option C: CDN / Edge Cache | Option D (local/cheap): In-Memory (app process) |
|---|---------|---------|---------|---------|
| What | Cache in application memory (LRU, TTL) | Shared cache across application instances | Cache at the network edge for static/semi-static content | Simple dictionary/map in process memory |
| Best for | Single-instance apps, hot data | Multi-instance deployments, session storage | Static assets, API responses that rarely change | Prototypes, single-process apps |
| Trade-off | Lost on restart, not shared across instances | Network latency, operational overhead | Stale data risk, purge complexity | Lost on restart, memory limits, not shared |
| Cost | Free | Redis hosting ($5-50/mo managed) | CDN costs (often free tier available) | Free |
| SOLID/DRY check | ✅ Simple | ✅ Scales horizontally | ✅ Offloads work from origin | ✅ Simplest possible |

**Invalidation strategies:** Time-based (TTL), event-based (publish on write), version-based (cache key includes version).

**Consequence:** Affects consistency model — more caching means more eventual consistency.

---

### Decision 5: Consistency Model

**Context:** How fresh does data need to be? Depends on caching strategy (Decision 4).

**Options:**

| | Option A: Strong Consistency | Option B: Eventual Consistency | Option C: Mixed (per-operation) |
|---|---------|---------|---------|
| What | Every read returns the most recent write | Reads may return stale data for a short window | Critical operations are strongly consistent; others are eventually consistent |
| Best for | Financial transactions, inventory counts, auth | Social feeds, analytics, recommendations | Most real-world applications |
| Trade-off | Higher latency, lower availability under partitions | Stale reads possible, conflict resolution needed | Complexity in deciding which operations need which model |
| Cost | Higher infrastructure cost (single-leader replication) | Lower cost (multi-leader, leaderless replication) | Moderate |
| SOLID/DRY check | ✅ Simple mental model | ⚠️ Must handle stale reads explicitly | ✅ Right tool for each job |

**Example:** "User profile updates can be eventually consistent (if you change your name, it's OK if it takes 5 seconds to show everywhere). But payment processing must be strongly consistent (no double charges)."

**Consequence:** Affects error handling and how the UI communicates data freshness.

---

### Decision 6: Migration Strategy

**Context:** How the schema evolves over time. Depends on database type (Decision 1).

**Options:**

| | Option A: Migration Tool (Flyway/Alembic/Prisma Migrate) | Option B: Manual SQL Scripts | Option C: Schema-Less (NoSQL) |
|---|---------|---------|---------|
| What | Versioned migration files, applied in order, tracked in DB | Hand-written SQL scripts, applied manually or via CI | No formal schema — application code handles structure |
| Best for | Teams, CI/CD pipelines, production databases | Simple projects, solo developers | Document databases, rapid iteration |
| Trade-off | Learning curve, tooling dependency | Error-prone, no rollback guarantee | Schema drift, harder to reason about data shape |
| Cost | Free (most tools are open source) | Free | Free (but hidden cost in debugging) |
| SOLID/DRY check | ✅ Versioned, repeatable | ⚠️ Manual = risk of inconsistency | ⚠️ Violates contract-based design |

**Consequence:** Affects deployment process and rollback capability.

---

## Part 2: API Design

4 decisions covering how clients communicate with the backend.

### Decision 7: API Style

**Context:** How the frontend (or other services) talks to the backend. May already be decided in Quick Architecture.

**Options:**

| | Option A: REST | Option B: GraphQL | Option C: gRPC |
|---|---------|---------|---------|
| What | Resource-based HTTP endpoints (GET /users, POST /orders) | Query language with single endpoint, client specifies shape | Binary protocol with strongly-typed service definitions |
| Best for | CRUD apps, public APIs, cacheable resources | Complex frontends, mobile apps (bandwidth-sensitive), multiple clients | Service-to-service communication, real-time streaming, high throughput |
| Trade-off | Over/under-fetching, many endpoints | Complex server implementation, caching is harder | Not browser-native (needs gRPC-web), binary debugging is harder |
| Cost | Free, universal tooling | Free, but ecosystem tooling cost | Free, but requires protobuf tooling |
| SOLID/DRY check | ✅ Each resource is a clear module | ✅ Single source of truth for data shape | ✅ Strong contracts via protobuf |

**Consequence:** Affects frontend data fetching strategy, documentation approach, and testing strategy.

---

### Decision 8: API Versioning

**Context:** How the API evolves without breaking existing clients. Depends on API style (Decision 7).

**Options:**

| | Option A: URI Path (/v1/, /v2/) | Option B: Header-Based (Accept: application/vnd.api.v2+json) | Option C: Evolution (additive changes only) |
|---|---------|---------|---------|
| What | Version in URL, each version is a separate set of endpoints | Version specified in request headers | Never remove/rename fields, only add new ones |
| Best for | Public APIs, clear version boundaries | APIs where URL shouldn't change | Internal APIs, rapid iteration |
| Trade-off | Multiple codepaths to maintain | Less discoverable, header complexity | Must be disciplined — no breaking changes ever |
| Cost | Code duplication across versions | Moderate | Lowest maintenance if disciplined |
| SOLID/DRY check | ⚠️ Violates DRY across versions | ✅ Single URL, versioned behavior | ✅ DRY — one evolving contract |

**Consequence:** Affects how breaking changes are communicated and how clients upgrade.

---

### Decision 9: Contract Design

**Context:** The shape of requests, responses, and errors. Depends on API style (Decision 7).

**Key decisions:**
- **Request format:** JSON body vs query params vs form data
- **Response envelope:** `{ data, meta, errors }` vs flat response vs JSON:API
- **Error format:** Standard error object with code, message, details, and request ID
- **Pagination:** Cursor-based (scalable) vs offset-based (simple) vs keyset

**Options for error format:**

| | Option A: Simple { error, message } | Option B: RFC 7807 Problem Details | Option C: Custom Envelope { success, data, error } |
|---|---------|---------|---------|
| What | Minimal error object | Standardized error format with type URI, title, status, detail | Consistent wrapper for all responses |
| Best for | Internal APIs, simple apps | Public APIs, standard compliance | APIs where clients want a uniform response shape |
| Trade-off | No standard, varies by endpoint | More verbose, requires understanding the spec | Every response has wrapper overhead |
| SOLID/DRY check | ⚠️ Inconsistency risk | ✅ Standard contract | ✅ Consistent contract |

**Consequence:** Affects frontend error handling and API documentation.

---

### Decision 10: Rate Limiting

**Context:** Protecting the API from abuse and ensuring fair use. Applies to all API styles.

**Options:**

| | Option A: Per-User Limits | Option B: Per-Endpoint Limits | Option C: Token Bucket | Option D (local/cheap): Simple In-Memory Counter |
|---|---------|---------|---------|---------|
| What | Each authenticated user gets N requests/minute | Different limits per endpoint based on cost | Tokens replenish at a fixed rate, each request costs tokens | Counter per IP/user in application memory |
| Best for | SaaS with user tiers | APIs with expensive and cheap operations | Smooth rate limiting with burst allowance | Single-instance prototypes |
| Trade-off | Need user identification on every request | Complex configuration per endpoint | More complex to implement and explain | Not shared across instances, lost on restart |
| Cost | Requires auth + storage (Redis) | Same | Same | Free |
| SOLID/DRY check | ✅ Clear per-user contract | ✅ Granular control | ✅ Flexible and fair | ✅ Simple |

**Consequence:** Affects API response headers (X-RateLimit-*), client retry logic, and pricing tiers.

---

## Part 3: Code Structure & Patterns

5 decisions covering how the codebase is organized.

### Decision 11: Module Organization

**Context:** How source code is structured into directories and modules. Depends on architecture pattern (monolith vs microservices).

**Options:**

| | Option A: By Layer | Option B: By Feature | Option C: Hybrid |
|---|---------|---------|---------|
| What | `controllers/`, `services/`, `models/`, `repositories/` | `users/`, `orders/`, `payments/` (each with its own controller, service, model) | Top-level by feature, internal by layer |
| Best for | Small apps, teams that think in layers | Medium-large apps, teams organized by product area | Most real-world apps |
| Trade-off | Cross-cutting changes touch many directories | Some duplication of patterns across features | Slightly more complex directory structure |
| Cost | Same | Same | Same |
| SOLID/DRY check | ⚠️ Changes often cross layers (violates SRP at directory level) | ✅ Each feature is self-contained (SRP) | ✅ Best of both |

**Consequence:** Affects how new features are added, how teams work in parallel, and how code is reviewed.

---

### Decision 12: Design Patterns

**Context:** Identify 2-3 patterns that solve actual problems in THIS project. Don't enumerate all patterns — only the ones that apply.

**Approach:** Based on the requirements and architecture decisions so far, identify specific problems and match patterns:

| Problem | Pattern | Example |
|---------|---------|---------|
| Multiple similar behaviors | Strategy | Different pricing calculators, different notification channels |
| Complex object creation | Factory / Builder | Creating orders with many optional fields |
| Cross-cutting concerns | Middleware / Decorator | Logging, auth, rate limiting applied to request handlers |
| Event-driven communication | Observer / Pub-Sub | Order created → send email, update inventory, log analytics |
| External service integration | Adapter / Gateway | Wrapping payment APIs so you can swap providers |
| Plugin/extension system | Plugin | Adding new skill types, new data sources |

**Consequence:** Pattern choices affect interface design and dependency direction.

---

### Decision 13: SOLID Check

**Context:** Validate the proposed structure against SOLID principles. Not a choice — a validation step.

Walk through each principle against the proposed structure:

| Principle | Question | What to Check |
|-----------|----------|---------------|
| **SRP** (Single Responsibility) | Does each module have one reason to change? | Flag god classes, modules doing too many things |
| **OCP** (Open/Closed) | Can you add features without modifying existing code? | Check if new features require editing existing modules |
| **LSP** (Liskov Substitution) | Can you swap implementations? | E.g., can you swap SQLite → PostgreSQL without changing business logic? |
| **ISP** (Interface Segregation) | Are interfaces focused or bloated? | Flag interfaces with methods that some implementations don't need |
| **DIP** (Dependency Inversion) | Do high-level modules depend on abstractions? | Check if business logic imports concrete database/API clients directly |

For each violation found, propose a specific fix.

---

### Decision 14: DRY/KISS/YAGNI Check

**Context:** Flag over-engineering or duplication. Not a choice — a validation step.

| Principle | Question | Red Flags |
|-----------|----------|-----------|
| **DRY** | Is there duplicated logic? | Copy-pasted validation, repeated error handling, duplicated queries |
| **KISS** | Is this the simplest solution? | Microservices for a 2-person team, Kubernetes for a prototype, event sourcing for a CRUD app |
| **YAGNI** | Are we building features we don't need yet? | Premature multi-tenancy, internationalization before first user, plugin system with one plugin |

For each violation found, propose a simpler alternative.

---

### Decision 15: Dependency Direction

**Context:** What depends on what. Circular dependencies indicate poor architecture. Depends on module organization (Decision 11).

**Validation:**
- Draw the dependency graph (which modules import which)
- Check for circular dependencies
- Verify that dependencies flow inward: UI → Application → Domain → Infrastructure (Clean Architecture) or similar
- Flag any case where a core module depends on an infrastructure module

**Options for fixing circular dependencies:**

| | Option A: Dependency Inversion | Option B: Extract Shared Module | Option C: Event-Based Decoupling |
|---|---------|---------|---------|
| What | Introduce an interface, have the dependency point to the abstraction | Move shared code to a common module both can import | Replace direct calls with events/messages |
| Best for | When two modules have a clear provider-consumer relationship | When the cycle is caused by shared types or utilities | When modules should be truly independent |

---

## Part 4: Data Flow

Not a decision area — a documentation exercise. After data and API decisions are made, diagram these three paths.

### Write Path
User action → input validation → business logic → data transformation → storage → confirmation/event emission

### Read Path
User request → authentication/authorization → cache check → database query → data transformation → response serialization → delivery

### Error Path
Failure at any stage → error classification (client error vs server error vs transient) → error response to caller → logging → alerting (if critical) → retry (if transient)

**Output:** ASCII flow diagram showing all three paths with the specific components from this architecture.

---

## Part 5: Extensibility

5 decisions covering how the system grows and accepts new functionality.

### Decision 16: Plugin/Extension Points

**Context:** Where can new functionality be added without modifying core code?

**Options:**

| | Option A: No Extension Points (YAGNI) | Option B: Hook-Based (lifecycle hooks, middleware) | Option C: Plugin Architecture (formal plugin API) |
|---|---------|---------|---------|
| What | Add features by editing existing code | Define hooks where external code can run (beforeSave, afterCreate, etc.) | Formal plugin interface with registration, discovery, and isolation |
| Best for | Small apps, solo developers, early-stage products | Medium apps that need customization points | Platforms, apps with third-party extensions |
| Trade-off | Simplest, but modification risk grows | Moderate complexity, clear extension boundaries | High upfront cost, but scales well |
| Cost | Zero | Moderate design effort | Significant design effort |
| SOLID/DRY check | ⚠️ Violates OCP | ✅ Supports OCP | ✅ Full OCP compliance |

**Consequence:** Affects interface contracts and versioning strategy.

---

### Decision 17: Interface Contracts

**Context:** What must new components implement? Depends on extension point design (Decision 16).

Define for each extension point:
- Required interface (methods/functions that must be implemented)
- Optional interface (methods with default behavior)
- Data contracts (input/output shapes)
- Error contracts (what errors can be thrown and how they're handled)

---

### Decision 18: Shared vs Isolated State

**Context:** What's shared across extensions? Depends on plugin architecture (Decision 16).

**Options:**

| | Option A: Shared State (global context) | Option B: Isolated State (each plugin has its own) | Option C: Shared Read, Isolated Write |
|---|---------|---------|---------|
| What | Extensions can read and modify shared application state | Each extension has its own state, communicates via messages | Extensions can read shared state but only write to their own |
| Best for | Tightly integrated extensions | Loosely coupled plugins, third-party extensions | Most real-world cases |
| Trade-off | Tight coupling, hard to reason about side effects | More complex communication, potential data duplication | Moderate complexity |
| SOLID/DRY check | ⚠️ Violates SRP — who owns the state? | ✅ Clear ownership | ✅ Balanced |

---

### Decision 19: Interface Versioning

**Context:** How do interfaces evolve without breaking existing extensions? Depends on interface contracts (Decision 17).

**Options:**

| | Option A: Semantic Versioning | Option B: Additive Only | Option C: Version Per Interface |
|---|---------|---------|---------|
| What | Major.minor.patch with breaking changes in major versions | Never remove/rename, only add | Each interface has its own version independent of others |
| Best for | Public APIs, plugin ecosystems | Internal extensions, rapid iteration | Large systems with many independent interfaces |
| Trade-off | Must maintain multiple versions during migration | Must be disciplined, old fields accumulate | More complex version tracking |
| SOLID/DRY check | ✅ Clear contracts | ✅ Backward compatible | ✅ Fine-grained control |

---

### Decision 20: Feature Toggles

**Context:** How to enable/disable features safely. Important for gradual rollouts and A/B testing.

**Options:**

| | Option A: Environment Variables | Option B: Config File / Database | Option C: Feature Flag Service (LaunchDarkly, Unleash) |
|---|---------|---------|---------|
| What | Simple on/off via env vars, requires restart | Toggles stored in config or DB, changeable at runtime | Managed service with targeting, rollout %, analytics |
| Best for | Small teams, few features | Medium teams, runtime control needed | Large teams, gradual rollouts, A/B testing |
| Trade-off | Requires redeploy to change, no targeting | Must build admin UI, no analytics | Cost, vendor dependency |
| Cost | Free | Free (build it) | Paid ($10-100+/mo) or self-hosted (Unleash is free) |
| SOLID/DRY check | ✅ Simple | ✅ Flexible | ✅ Full-featured |

**Local/cheap alternative:** Environment variables or a JSON config file.

---

## Decision Format Reference

Each decision above follows the standard format from the base SKILL.md. For guardrails (G-ARCH-1 through G-ARCH-4, G1-G9), see `shared/guardrails.md` — they are not duplicated here.
