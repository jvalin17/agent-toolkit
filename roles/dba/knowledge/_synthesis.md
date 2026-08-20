---
role: dba
sources: 7
synthesized_at: 2026-08-17T00:50:08.488044
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
This role covers database server tuning, schema design, indexes, migrations, replication, backup, and query plans. Knowledge synthesized from 5 usable sources (drizzle-orm, PostHog, prisma-examples, Saleor, Supabase). **Two URL sources failed extraction** (PostHog ClickHouse event-store blog, Uber Schemaless blog) — re-fetch with headless browser recommended; nothing from them is included.

---

## Patterns Found (ranked by frequency)

### 1. Migration-as-code with sequential ordering (4/5 repos)
- **Supabase**: timestamped SQL files, forward-only, no down-migrations: `supabase/migrations/20230126220613_doc_embeddings.sql`
- **Saleor**: standard Django numbered migrations per app; manual invocation (`python manage.py migrate`), not auto-run on container start
- **PostHog**: Django migrations for Postgres + **separate ClickHouse migration track** (`posthog/clickhouse/migrations/`) + custom async-migration framework for multi-hour changes
- **drizzle-orm**: snapshot-diff-generated SQL migrations (see Pattern 3)

### 2. Lock-safe DDL on large tables (2/5, both explicit)
- **PostHog** — dedicated migration helpers:
  ```python
  # posthog/migration_helpers/concurrent_index.py      → CREATE INDEX CONCURRENTLY
  # posthog/migration_helpers/not_valid_constraint.py  → ADD CONSTRAINT ... NOT VALID
  # then VALIDATE CONSTRAINT as separate migration step
  ```
- **Saleor** — explicit named indexes decoupled from ORM defaults (see Pattern 4), enabling `DROP INDEX CONCURRENTLY` outside ORM

### 3. Snapshot diffing for migration generation (drizzle-orm)
Compare JSON snapshots of schema state, not SQL AST:
```typescript
// drizzle-kit/src/snapshotsDiffer.ts
applyPgSnapshotsDiff(squashedPrev, squashedCur, tablesResolver, columnsResolver, ...)
```
Rename-vs-drop ambiguity resolved via injected **resolver callbacks** (format `"public.old->public.new"`) to prevent accidental data loss. Supabase does the inverse — periodic `remote_schema.sql` snapshot migrations for drift detection.

### 4. Explicit named indexes over ORM defaults (Saleor)
```python
product = models.ForeignKey(Product, ..., db_index=False)  # suppress default
class Meta:
    indexes = [BTreeIndex(fields=["product"], name="assignedprodattrval_product_idx")]
```
Named indexes are referenceable in `EXPLAIN` / manageable without ORM. Applied selectively to high-volume FK columns only.

### 5. Explicit through-tables + composite unique constraints (Saleor)
All M2M relationships use explicit through tables with `unique_together` natural keys:
```python
class AssignedVariantAttribute(BaseAssignedAttribute):
    class Meta:
        unique_together = (("variant", "assignment"),)
```
Allows extra columns (`sort_order`), named indexes, controlled cascades.

### 6. Physical database separation by workload (PostHog, Saleor)
- **PostHog**: separate Postgres DBs per concern — persons/identity, flags read store, job queue (cyclotron), cohorts, catalog (`docker/postgres-init-scripts/create-*-db.sh`)
- **Saleor**: separate Redis DBs — DB 0 cache, DB 1 Celery broker

### 7. Row-level locking for concurrency (Saleor)
Per-domain `lock_objects.py` (checkout, order, payment, giftcard) + ADR `0004-race-safe-balance-adjustments.md` — DB-level locking (`SELECT FOR UPDATE` pattern) for balance columns.

---

## How Problems Are Solved

**PROBLEM: Long-running schema changes on huge tables**
- PostHog: custom async migration framework (`posthog/async_migrations/runner.py`) — `operations[]`/`rollback_operations[]`, progress tracked in Postgres, pause/resume. Used for ClickHouse `ORDER BY` rebuilds taking hours/days.
- PostHog backfills: Dagster DAGs with range-based chunking (`backfill_materialized_column.py`)

**PROBLEM: JSON property query performance (ClickHouse)**
- PostHog: materialized columns extracted from JSON with full lifecycle DAGs (create/index/backfill/drop) + bloom-filter skip indexes (`posthog/clickhouse/indexes.py`, `property_groups.py`)

**PROBLEM: Data deletion in append-optimized stores**
- PostHog: soft-delete in Postgres → async job → ClickHouse `ALTER TABLE ... DELETE` mutation, with trigger logging

**PROBLEM: N+1 queries**
- Saleor: GraphQL DataLoaders + `pytest-django-queries` query-count assertions in CI
- prisma-examples: eager loading via `include: { posts: true }` everywhere (no pagination shown; over-fetches — counts computed in app memory instead of `_count`)

**PROBLEM: Vector search in Postgres**
- Supabase: pgvector in Postgres (not a separate vector DB), evolved over 7 migration phases; **hybrid search** = `tsvector` column + `vector` column on same table (double index/write-amp cost accepted)

**PROBLEM: Deterministic ordering**
- Saleor: `sort_order` column with `ordering = ("sort_order", "pk")` — pk tiebreaker

**PROBLEM: Query observability & runaway queries**
- PostHog: query tagging (team_id, query_type, user) in `query_tagging.py`; `system.query_log` archived to S3; `cancel.py` kills runaway queries; `explain.py` wraps `EXPLAIN PIPELINE`

---

## Architecture Decisions Seen

| Decision | Choice | Repos | Tradeoff noted |
|---|---|---|---|
| OLTP/OLAP split | Postgres (metadata) + ClickHouse (events), dual models per entity | PostHog | Two migration systems, denormalization DAGs (persons-on-events) to kill joins |
| Single-engine everything | Postgres for auth, storage metadata, vectors, realtime | Supabase | Postgres bears ANN index memory/compute |
| Forward-only migrations | No down scripts | Supabase | Rollback = new forward migration or PITR |
| Authorization layer | RLS in Postgres as primary access control | Supabase (also drizzle supports RLS resolvers) | Per-row policy eval cost; debugging needs DB access |
| Connection pooling | Dedicated pooler service (Supavisor/PgBouncer) | Supabase | Extra hop/service. prisma-examples: **no pool config at all** (relies on defaults/Accelerate) |
| PG version upgrades | Scripted + tested (`upgrade-pg17.sh`, `upgrades.json` manifest, test scripts) | Supabase | — |
| Ingestion path | Kafka → ClickHouse Kafka engine table → MV → ReplicatedMergeTree; DLQ table for failures | PostHog | — |
| Scheduled jobs | Celery Beat schedules stored in DB (`DatabaseScheduler`) | Saleor | Live schedule changes, but adds DB polling |
| Schema-per-database vs shared | Independent schema per DB target | prisma-examples | Schema drift observed (fields exist in one target, not another) |
| Push vs migration files | Both: generated SQL files OR direct push with destructive-op warnings (`logSuggestionsAndReturn`) | drizzle-kit | — |

---

## Testing Approaches
- **Real databases, not mocks**: PostHog (real ClickHouse), Supabase (e2e vs live Postgres), prisma-examples (docker-compose DBs, 5-min test timeouts), drizzle (pglite/better-sqlite3/mysql2 in tests)
- **Query-count budgets**: Saleor `pytest-django-queries` — N+1 regression prevention
- **Migration helpers unit-tested against real DB**: PostHog `test_concurrent_index.py`, `test_not_valid_constraint.py`
- **Upgrade-path tests**: Supabase shell scripts (`test-pg17-upgrade.sh`, `test-upgrades-manifest.sh`)
- **Concurrency test helpers**: Saleor `tests/race_condition.py`
- **Performance benchmarks over time**: PostHog ASV suite (`ee/benchmarks/`)
- **Type-gen as schema validation**: Supabase `supabase gen types typescript` — type errors surface drift
- **Test-DB reuse**: Saleor `--reuse-db` + `-n=auto` parallel execution

## Deployment & Production
- **Config fragments**: PostHog ClickHouse `config.d/` XML merge pattern; separate prod/dev `users.xml`
- **Connection budget awareness**: Saleor — 3 process types (web/worker/beat) each with own connections; uvicorn `--limit-max-requests=10000` recycles workers (releases held connections)
- **Backup**: PostHog Dagster DAG (`dags/backups.py`); query-log archival to S3. Supabase: no explicit dump scripts visible
- **Operational runbooks as scripts**: Supabase key rotation (`rotate-new-api-keys.sh`, `db-passwd.sh`), owner reassignment post-restore (`reassign-owner.sh`)
- **Replication**: PostHog ReplicatedMergeTree + `ON CLUSTER` abstraction (`cluster.py`); drizzle tests replica-aware routing (`integration-tests/tests/replicas/`); PostHog flags read-store DB is effectively a read-path split
- **Part maintenance**: PostHog `part_breaker.py` DAG splits oversized ClickHouse parts
- **Observability**: Saleor OpenTelemetry + Sentry; PostHog query tagging + admin API for active queries

## Open Questions (for reviewer)
1. **Down-migrations**: Supabase is forward-only; Django repos support reversal; PostHog async framework has explicit `rollback_operations[]`. Which policy to adopt?
2. **Index naming**: Saleor names indexes selectively (high-volume only); should named indexes be universal?
3. **Aggregation location**: prisma-examples counts in app memory (`user.posts.length`) — anti-pattern at scale or acceptable for demos? Flag for guidance.
4. **Connection pooling**: dedicated pooler service (Supabase) vs no visible config (prisma-examples) vs per-process defaults (Saleor). No consensus.
5. **Authorization in DB (RLS) vs app layer** — only Supabase commits to RLS-first; performance implications unresolved.
6. **Failed sources**: P
