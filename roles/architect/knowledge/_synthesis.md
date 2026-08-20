---
role: architect
sources: 7
synthesized_at: 2026-08-17T02:10:40.973566
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Architect scope covers system decomposition (services, bounded contexts, monorepos), data architecture (polyglot persistence, consistency models), integration patterns (event buses, plugin systems, contracts), capacity planning, and formal decision-making (ADRs, tradeoff analysis). Sources span two reference frameworks (Fowler microservices, AWS Well-Architected), one study repo (system-design-primer), and four production codebases (Kubernetes, Cal.com, PostHog, Supabase).

## Patterns Found (ranked by frequency)

**1. Plugin/Registry Pattern (5/7 repos)** — decouple orchestrator from implementations via registration against typed interfaces.
- Kubernetes: scheduler plugins (`pkg/scheduler/framework/`), admission chains, per-resource registries (`rest.go`, `strategy.go`, `storage/`)
- Cal.com: app-store — each integration is a package implementing typed contracts (`Calendar.d.ts`, `VideoApiAdapter.d.ts`, `PaymentService.d.ts`); factory selects implementation at runtime
- PostHog: HogAI tool registry (`ee/hogai/registry.py`), query runner routing
- Supabase: component registry (`__registry__/`), pluggable storage backends (S3/RustFS compose variants)
- system-design-primer: documents Strategy pattern (parking_lot)

**2. Event Bus / Async Decoupling (4/7)** — "smart endpoints, dumb pipes."
- Fowler: RabbitMQ/ZeroMQ as routing-only infrastructure; ESB explicitly rejected
- PostHog: Kafka-as-bus — all ingestion via topics (`posthog/kafka_client/topics.py` is canonical registry); no direct DB writes
- Kubernetes: watch/informer pattern — controllers never poll, react to cache events from API server watch streams
- Cal.com: Trigger.dev for durable async workflows (post-booking actions)

**3. Reconciliation / Eventual Consistency (3/7)**
- Kubernetes: every controller = watch → queue → reconcile loop (`pkg/controller/*/`); no distributed transactions
- Fowler: compensating operations instead of 2PC; "cost of fixing mistakes < cost of coordination"
- PostHog: async deletion with trigger log (`posthog/dags/deletes.py` — deletions persisted first, DAG processes queue); person-ID override reconciliation DAGs

**4. Monorepo with Publishing/Boundary Discipline (4/7)**
- Kubernetes: staging dirs (`staging/src/k8s.io/`) published to separate repos; import direction enforced by `cmd/import-boss/`
- Cal.com: Turborepo + Yarn workspaces; `apps/*` (deployable) vs `packages/*` (shared) vs `packages/features/*` (domain)
- Supabase: Turborepo + pnpm workspaces
- PostHog: polyglot monorepo (Python/Node/Go/Rust/C++) with per-directory `owners.yaml`

**5. Layered Type/Contract Boundaries (4/7)**
- Kubernetes: internal types (`pkg/apis/core/types.go`) separate from versioned wire types; conversion functions isolate API evolution
- Cal.com: DTO boundaries — Prisma models don't leak across layers (`agents/rules/data-dto-boundaries.md`)
- Supabase: OpenAPI codegen (`packages/api-types/redocly.yaml`) — types generated from spec
- PostHog: JSON IDL (`posthog/idl/events_json.json`) feeds ClickHouse schemas, Kafka topics, Python models

**6. Feature Flags as Architecture (4/7)** — gate rollouts, not just UX.
- Kubernetes: centralized gates (`pkg/features/kube_features.go`)
- Cal.com: DB-stored flags (Prisma), not env vars
- PostHog: Redis-cached flag evaluation on hot path
- Supabase: ConfigCat SDK in shared `common` package

**7. Vertical Slice / Bounded Context Organization (3/7)**
- Fowler: services around business capabilities (Conway's Law); bounded contexts → service boundaries
- Cal.com: `packages/features/<domain>/` with `components/`, `lib/`, `repository/`, `types/` per slice
- PostHog: EE/OSS split (`ee/` conditionally loaded), domain-grouped modules

**8. CQRS / Query Encapsulation (2/7)**
- PostHog: every analytics query is a runner class (`calculate()`, `to_query()`, `to_hogql()`); frontend sends query node, backend routes to runner
- Cal.com: repository pattern — data access behind repository classes, thin controllers

## How Problems Are Solved

**PROBLEM: Distributed data consistency**
- Fowler: eventual consistency + compensating operations; reject 2PC
- Kubernetes: etcd sole store, all writes through API server; reconciliation loops converge state
- PostHog: denormalize (persons-on-events) + reconciliation DAGs for merges

**PROBLEM: Service contract evolution**
- Fowler: Consumer-Driven Contracts (contract-first, executed in CI) + Tolerant Reader
- Cal.com: `agents/rules/api-no-breaking-changes.md`; versioned API dir (`apps/api/v2/`); changesets for SDK versioning
- Kubernetes: versioned API groups with conversion layer; CRDs + aggregation for extension

**PROBLEM: Large-scale framework migration**
- Supabase: parallel-run strategy — Studio mid-migration Next.js→TanStack with `compat/` bridge and build flag (`STUDIO_FRAMEWORK=tanstack`), not big-bang rewrite

**PROBLEM: Cascading failure**
- Fowler: circuit breaker, design-for-failure as first-class requirement
- Kubernetes: API Priority & Fairness (`FlowSchema`/`PriorityLevelConfiguration`) prevents workload starvation; leader election via Lease objects for HA

**PROBLEM: Capacity planning**
- system-design-primer: back-of-envelope template — QPS, storage over time, read/write ratio, cache memory (e.g., pastebin: "1M writes/mo × 10KB = 10GB/mo"); progressive scaling path: single box → split web/DB → LB → CDN → cache → read replicas → autoscale → multi-AZ
- Database scaling ladder: read replicas → federation → sharding → denormalization → SQL tuning

**PROBLEM: Right store per workload**
- PostHog: ClickHouse for events, Postgres for metadata, multiple isolated Postgres DBs per domain (persons, flags-read, job queues), DuckDB warehouse emerging
- Supabase: pgvector in Postgres for semantic search (avoid separate vector DB)
- system-design-primer: SQL vs NoSQL tradeoff matrix; CAP as system-level choice (CP: HBase/ZooKeeper; AP: Cassandra)

**PROBLEM: Hot-path vs business-logic split**
- PostHog: Node.js for ingestion throughput, Django for ORM/business logic, Go for SSE fan-out (Django unsuitable for long-lived connections), Rust for ClickHouse UDFs

**PROBLEM: Idempotency**
- Cal.com: explicit idempotency key module (`packages/lib/idempotencyKey/`) on booking operations

## Architecture Decisions Seen

| Decision | Choice | Repos | Tradeoff noted |
|---|---|---|---|
| Services vs libraries | Out-of-process services | Fowler | Coarser APIs required; remote call cost |
| Shared DB vs per-service DB | Decentralized/polyglot | Fowler, PostHog | Eventual consistency cost |
| Internal vs external API | tRPC internal / REST v2 external | Cal.com | Two API surfaces to maintain |
| Orchestration | Choreography over central orchestrator; but Dagster for data pipelines, Celery for short tasks | Fowler, PostHog | Dagster chosen where dependency graphs matter |
| Governance | Decentralized, internal open-source model | Fowler, Kubernetes | Technology proliferation risk |
| Review posture | Conversation over audit gate | AWS WAF | Encourages honest disclosure |
| Evaluation model | Question-driven pillars (reliable/secure/efficient/cost/sustainable) | AWS WAF | — |
| Extensibility | Two tiers: schema-driven (CRDs) + full extension servers (aggregation) | Kubernetes | Boilerplate vs power |
| Ownership | "You build it, you run it"; `owners.yaml` per directory | Fowler, PostHog | — |
| Gateway | Multiple interchangeable options (Kong/Nginx/Caddy/Envoy) | Supabase | Config matrix growth |
| Zero-downtime migrations | First-class helpers (`CONCURRENTLY`, `NOT VALID` wrappers) | PostHog | — |

## Testing Approaches
- **Contract tests in CI**: consumer-driven contracts as build gate (Fowler)
- **Layered pyramid**: unit (table-driven, fake clients) → integration (`test/integration/`) → e2e (Ginkgo/Gomega) — Kubernetes
- **Test modes via env**: `VITEST_MODE=integration|timezone|packaged-embed` — Cal.com
- **Infra-path shell tests**: upgrade paths, storage backends tested pre-release (`docker/tests/test-pg17-upgrade.sh`) — Supabase
- **Scoped E2E**: run only suites affected by changed files (`e2e/shared/resolve-scope-cli.ts`) — Supabase
- **Synthetic monitoring as tests**: Checkly checks in repo (`__checks__/`) — Cal.com
- **Architecture rules as lint**: circular-dep prevention, no-quadratic-algorithms, select-over-include codified in `agents/rules/` — Cal.com

## Deployment & Production
- **CD pipeline per service, "make deployment boring"** (Fowler); build → test → promote stages
- **Dual deployment modes**: cloud SaaS + self-hosted Docker with same codebase (Supabase, PostHog EE/OSS split)
- **Observability stack convergence**: OpenTelemetry (K8s, Cal.com, Supabase), Sentry (Cal.com), structured leveled logging (klog in K8s), query tagging for per-team CH observability (PostHog)
- **Separate binaries communicating only through API server** — no direct component RPC (Kubernetes)
- **Centralized egress layer** for all outbound HTTP: rate limiting + observability + transport abstraction (PostHog)
- **Explicit upgrade manifests** (`docker/upgrades.json`) and scripted upgrade paths (Supabase)

## Open Questions (for reviewer)
1. **Monorepo vs service-per-repo**: all four codebases are monorepos, but
