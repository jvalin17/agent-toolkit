---
role: data-engineer
sources: 5
synthesized_at: 2026-08-17T01:37:41.294797
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Data-engineer knowledge synthesized from 5 repos: Airbyte (connectors/EL), Dagster (orchestration), dbt-core v2 (transformation/T), Great Expectations (data quality), PostHog (production analytics platform). Together they cover the full pipeline lifecycle: extraction, orchestration, transformation, quality validation, streaming ingestion, and warehouse management.

## Patterns Found (ranked by frequency across repos)

**1. Pluggable execution/adapter backend abstraction** — 4/5 repos
- GX: Strategy pattern — `execution_engine/{pandas,sparkdf,sqlalchemy}_execution_engine.py`; same expectation runs on any backend
- dbt: 3-tier adapters — `dbt-adapter-core` (traits) → `dbt-adapter-sql` (dialects) → `dbt-adapter` (wiring); per-dialect lexer crates (`dbt-lexer-snowflake`, etc.)
- Dagster: I/O managers per backend (`dagster-duckdb-pandas`, `dagster-deltalake-polars`, `dagster-snowflake`)
- Airbyte: CDK per language (Python/Java/Kotlin), connectors depend on CDK one-directionally

**2. Monorepo with module boundaries** — 4/5 repos (Airbyte, Dagster, dbt, PostHog)
- Airbyte: 600+ connectors + shared CDK; atomic CDK updates, `get-modified-connectors.sh` for selective CI
- dbt: crate-per-pipeline-stage (`dbt-loader`, `dbt-compilation`, `dbt-dag`, `dbt-scheduler`, `dbt-freshness`, `dbt-defer`, `dbt-state`)
- Dagster: core + 40+ integration libraries + Helm + examples

**3. DAG-based dependency resolution** — 3/5 repos
- Dagster: asset-oriented — declare *what data to produce*, execution order derived from asset deps: `@dg.asset def model(upstream: pd.DataFrame): ...`
- GX: metric dependency graph (`validator/validation_graph.py`) — computes only metrics needed for requested expectations, keyed `(metric_name, domain, parameters)`
- dbt: `dbt-dag` crate using `petgraph`; `dbt-selector-parser` for `tag:marketing+` expressions
- PostHog: uses Dagster DAGs for batch ops (`dags/backfill_materialized_column.py`, `dags/deletes.py`)

**4. Builder / fluent configuration** — 3/5 repos
- Airbyte tests: `JobStatusResponseBuilder().with_completed_status(id, url).build()`
- GX: fluent datasource API (`datasource/fluent/`) alongside legacy YAML config
- Dagster: frozen dataclass API wrappers (`@dataclass(frozen=True) class DgApiRunApi`)

**5. Compatibility shim for optional dependencies** — 2/5 repos
- GX: `compatibility/{sqlalchemy,pyspark,bigquery,...}.py` with `not_imported.py` stubs — graceful degradation; also Pydantic v1/v2 dual support
- dbt: `[patch.crates-io]` fork-and-patch for DataFusion/Arrow/sqlparser at git commit level

**6. Generated code separated from hand-written** — 2/5 repos
- Dagster: `__generated__/` GraphQL types, excluded from ruff
- PostHog: ANTLR-generated HogQL parser (C++ → WASM/Python)

**7. Exhaustive discriminated-union error handling** — Dagster
```python
match result.typename__:
    case "Run": return DgApiRun(...)
    case "RunNotFoundError": raise DagsterPlusGraphqlError(...)
    case _ as unreachable: assert_never(unreachable)
```

## How Problems Are Solved

**PROBLEM: High-volume extraction from APIs**
- Airbyte/Shopify: async Bulk GraphQL job (submit → poll `RUNNING`→`COMPLETED` → fetch JSONL from pre-signed URL) instead of cursor pagination. Parent-child records flattened with `__parentId` links. Explicit cancel handling (`bulkOperationCancel`).
- Dagster API: cursor-based pagination (`list_runs(limit=50, cursor=None)` returning `items` + `total`)

**PROBLEM: Incremental sync / avoiding recomputation**
- Airbyte: time-window cursor baked into query — `updated_at:>='%LOWER_BOUNDARY_TOKEN%'` with isoformat substitution
- dbt: `dbt-defer` + `dbt-state` crates — skip unchanged models based on prior run state
- PostHog: `refresh_policy.py` — staleness tolerance per query; cache keys = team ID + query hash, zstd-compressed in Redis
- Dagster: partition tag injection — `ExecutionTag(key="dagster/partition", value=partition)`

**PROBLEM: Failed record handling**
- PostHog: dead letter queue (`clickhouse/dead_letter_queue.py`, DLQ IDL schema) for ingestion failures; fail-open DB backend
- dbt: `reqwest-retry` middleware for cloud API resilience
- GX: typed exception hierarchy incl. dedicated `resource_freshness.py` staleness errors

**PROBLEM: Data quality in pipelines**
- GX: Checkpoint = datasource + suite + actions (Slack/PagerDuty/DataDocs hooks) — the Airflow/Prefect/Dagster integration point; suite parameters for dynamic thresholds; raw-SQL expectations for business logic
- Dagster: dbt tests + asset checks (`examples/data-quality-patterns/`)
- dbt: `dbt-freshness` crate for source freshness thresholds

**PROBLEM: Identity/entity mutation at scale (warehouse)**
- PostHog: person-ID override table merged at query-compile time — never mutates event records (`dags/fix_person_id_overrides.py`)
- PostHog: materialized column lifecycle as explicit DAGs — create → backfill → add index → drop

**PROBLEM: Slicing data for validation/processing**
- GX: `Batch`/`BatchSpec`/`BatchDefinition` + partitioners (by date, integer range, column value), separate from execution

**PROBLEM: Large schema migrations**
- PostHog: two-tier — Django migrations + custom async migration framework for large ClickHouse ops with status tracking

## Architecture Decisions Seen

| Decision | Choice | Tradeoff noted |
|---|---|---|
| Asset model vs task DAG | Dagster: declarative assets; PostHog uses both Dagster + Temporal + Celery + custom Cyclotron | Assets derive ordering from deps; multiple orchestrators = operational complexity |
| Multi-store separation | PostHog: Postgres (operational) / ClickHouse (events) / Kafka (transport) / Redis (cache+pubsub) / S3 (blobs); separate Postgres DBs per concern (persons, cohorts, cyclotron) | Isolation vs cross-store consistency burden |
| Internal SQL dialect | PostHog HogQL → ClickHouse SQL (access control at compile time); dbt Jinja-SQL → dialect SQL via embedded MiniJinja-in-Rust | Powerful abstraction, high maintenance |
| Artifact format | dbt v2: Parquet artifacts (queryable) + JSON for backcompat; Arrow IPC/Flight for zero-copy transport | Columnar tooling required |
| Rewrite vs extend | dbt: ground-up Rust rewrite, single binary, no Python runtime | Parallel v1 branch maintenance |
| Connector delivery | Airbyte: Docker image per connector (java/python/manifest-only Dockerfiles); reproducible builds (no timestamps, sorted archives) | |
| Polyglot by workload | PostHog: Python API, Node.js ingestion, Go livestream, Rust UDFs | Perf per concern vs team fragmentation |
| Emerging dual engine | PostHog building DuckDB/DuckLake alongside ClickHouse | Migration hedge |

## Testing Approaches

- **HTTP mocking over live APIs** (Airbyte): `HttpMocker` pre-registers request→response pairs; `ANY_QUERY_PARAMS` sentinel; JSON fixture templates via `find_template()`; randomized record IDs to prevent hard-coded coupling. Tradeoff: won't catch API contract drift.
- **Docker per backend** (GX): `assets/docker/{postgresql,mysql,spark,trino,clickhouse,...}` for local integration tests
- **Declarative test cases** (GX): expectation tests as data structures in `test_definitions/`, run against known inputs/outputs
- **Minimum-version constraint testing** (GX): `ci/constraints-test/` pins pandas2-min, pydantic-v1, py310-min
- **Interface substitution** (Dagster): `IGraphQLClient` protocol enables mock clients
- **Test categorization**: Dagster strict pytest markers (`integration`, `slow`), 240s hard timeout; Airbyte JUnit class-level parallel / method-level serial, 1m default timeout
- **CI-enforced coverage** (GX): `check_integration_test_gets_run.py` — new datasources must have integration tests
- **Record/replay** (dbt): `adbc-record-replay` crate for database I/O testing
- **CI vs local strictness** (Airbyte): warnings-as-errors only in CI (`System.getenv("CI")`)

## Deployment & Production

- **Kubernetes primary**: Dagster full Helm chart (`values.schema.json`); also Docker Compose (local), ECS+Terraform, cloud/hybrid
- **Containerized units**: Airbyte per-connector Docker images; Dagster separates orchestrator vs user-code images (`Dockerfile_dagster` / `Dockerfile_user_code`)
- **Observability**: dbt — OpenTelemetry OTLP + `tracing` with JSON output + Tracy profiler; PostHog — query tagging, ClickHouse query log archived to S3 via DAG for cost analysis; Dagster — `dagster-datadog`
- **Secrets/CI**: Airbyte dedicated `ci_credentials` module; env-var config with `${}` substitution (GX `config_provider.py`); dotenv support (dbt)
- **Ownership**: PostHog `owners.yaml` per module
- **Reproducibility**: Airbyte deterministic archives; dbt workspace-pinned deps; Dagster per-package `uv.lock`

## Open Questions (for reviewer)

1. **Pagination vs bulk-job extraction**: Airbyte chose async bulk jobs (throughput) vs Dagster's cursor pagination (simplicity). Which is default guidance for new pipelines?
2. **Orchestrator proliferation**: PostHog runs Dagster + Temporal + Celery + Cyclotron simultaneously. Endorse single-orchestrator or workload-specific tools?
3. **Test realism**: Airb
