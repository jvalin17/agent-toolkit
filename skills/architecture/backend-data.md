# Backend: Data & API Architecture
Keywords: database, schema, SQL, NoSQL, caching, consistency, migrations, REST, GraphQL, API, versioning, rate limiting

Data storage and API design decisions. 10 decisions in waterfall order.

**Rules from real usage:**
- Threading/concurrency: flag known issues for chosen DB+framework combo (SQLite + threaded workers = crash).
- Parsing logic (URL, document, data extraction) must be standalone reusable module, not coupled to any service.
- Domain knowledge that changes over time (ATS rules, formatting standards) = updatable config file, not hardcoded.

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
