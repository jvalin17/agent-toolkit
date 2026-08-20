---
role: infrastructure
sources: 7
synthesized_at: 2026-08-17T01:07:59.998067
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Infrastructure knowledge synthesized from 5 usable repos (crossplane, gitea, jellyfin, signoz, docker-awesome-compose) plus one rendered edge-delivery page (blog-cloudflare-com-workers). **Note: `tagged-chaos-engineering` was Cloudflare-blocked — zero content extracted; exclude or re-fetch.** Coverage spans containers, monolith deployment, caching, rate limiting, migrations, observability, and graceful degradation.

## Patterns Found (ranked by frequency across repos)

**1. Single-binary monolith (4/5 repos)** — crossplane (all controllers in `cmd/crossplane/main.go`), gitea (HTTP+SSH+workers+CLI in one binary), jellyfin (modular monolith, multi-project .NET), signoz (all subsystems + embedded Prometheus/Alertmanager/OpenFGA in-process). Tradeoff noted everywhere: simpler ops vs. shared failure domain / no independent scaling.

**2. Numbered, forward-only DB migrations (3 repos)**
- gitea: `modelmigration/v1_27/v342.go`, each `func(x *xorm.Engine) error`, no rollback
- jellyfin: attribute-decorated migrations + `PreStartupRoutines/` for non-DB migrations, backup-before-migrate via `JellyfinMigrationBackupAttribute`
- signoz: `pressly/goose/v3` SQL migrations (SQLite + Postgres dialects)
- awesome-compose: up/down SQL files (`0001_create-users_up.sql`)

**3. Pluggable backend via interface + factory/registry (3 repos)**
- signoz: `pkg/factory/registry.go`; every subsystem has `noop*` impl (`nooplicensing/`, `noopemailing/`) for CE/disabled features
- gitea: auth strategy chain (`services/auth/group.go` — first success wins: session→basic→oauth2→reverseproxy)
- jellyfin: `IAuthenticationProvider` strategies, `IConfigurationFactory` per subsystem

**4. Two-tier caching: in-process + Redis (2 repos)**
- gitea: `modules/cache/cache_twoqueue.go` (LRU) + `cache_redis.go` + per-request context cache
- signoz: `memorycache`/`rediscache` behind one interface; time-bucketed query cache (`pkg/querier/bucket_cache.go`) enabling partial cache hits on sliding windows

**5. Rate limiting / load shedding middleware (3 repos)**
- gitea: `routers/common/qos.go` + `blockexpensive.go` (blocks expensive ops under load)
- crossplane: circuit breaker + token bucket (`internal/circuit/breaker.go`, `token_bucket.go`) with Prometheus metrics per breaker state
- jellyfin: `RateLimitExceededException` in middleware chain

**6. Distributed locking with single-node fallback (2 repos)** — gitea `modules/globallock/` (memory_locker vs redis_locker), crossplane package Lock CRD.

**7. Graceful degradation / timeout-with-fallback (2 sources)**
- cloudflare-blog: `Promise.race([componentReady, 8s timeout])` → disable search button; module import retry with timestamp appended to URL **fragment** (bypasses browser cache without polluting CDN cache key)
- gitea: SIGUSR2 graceful restart with socket FD inheritance (`modules/graceful/net_unix.go`), in-flight request draining

## How Problems Are Solved

**PROBLEM: CRD/schema lifecycle without Helm hooks** → crossplane owns CRD install/migration in-process (`internal/initializer/crds.go`, `crds_migrator.go`) via an initializer chain (crds → certs → lock → webhooks → tls), because Helm CRD hooks can't upgrade or protect.

**PROBLEM: Webhook TLS without cert-manager** → crossplane generates self-signed certs at startup (`cert_generator.go`) and injects CA into webhook configs.

**PROBLEM: Secrets in compose** → awesome-compose uses file-based secrets (`db/password.txt` → `/run/secrets/<name>`) instead of env vars, avoiding exposure in `docker inspect`.

**PROBLEM: Service startup ordering** → awesome-compose: healthcheck script + `depends_on: condition: service_healthy`. jellyfin: two-phase startup (SetupServer serves status UI before main server ready). crossplane: ordered initializer chain before controllers start.

**PROBLEM: Out-of-process extensions** → crossplane runs composition functions as gRPC pods (protobuf I/O, `proto/fn/v1/`); jellyfin loads plugins via per-plugin `AssemblyLoadContext` (version isolation); gitea's git hooks call a private local HTTP API (`routers/private/hook_*.go`) instead of touching the DB directly.

**PROBLEM: Multi-writer field conflicts on K8s objects** → crossplane uses Server-Side Apply with managed-field stripping (`internal/ssa/managed_fields.go`).

**PROBLEM: Dependency resolution for packages** → crossplane explicit DAG with topological sort (`internal/dag/dag.go`), fuzz-tested.

**PROBLEM: Self-monitoring** → gitea: Prometheus `/metrics` + jsonnet/grafonnet Grafana mixin with alerts-as-code (`contrib/grafana-monitoring-mixin/`). signoz: OTel SDK self-instrumentation (`pkg/instrumentation/`). jellyfin: `ResponseTimeMiddleware` + single DB health check at `/health`. awesome-compose: Prometheus scrape config + Grafana datasource provisioned via YAML file (no UI setup).

**PROBLEM: Log aggregation** → awesome-compose ELK: Logstash reads mounted `nginx.log` file → Elasticsearch → Kibana (file-based, not stdout driver — noted as demo simplification).

## Architecture Decisions Seen

| Decision | Choices observed | Provenance |
|---|---|---|
| Embedded vs external deps | Embed Prometheus/Alertmanager/OpenFGA as libraries (signoz); embed SQLite (gitea, jellyfin, signoz CE) vs Postgres for EE (signoz) | signoz, gitea, jellyfin |
| CE/EE split | `pkg/` shared, `ee/` overrides, `noop*` for disabled features; separate Dockerfiles per edition | signoz |
| Feature flags | Runtime gates: `internal/features/features.go` (crossplane), `pkg/flagger/` + open-feature SDK (signoz) | crossplane, signoz |
| Container hardening | Rootless image as first-class variant (`docker/rootless/`), multi-arch manifests | gitea, signoz (`Dockerfile.multi-arch`) |
| Config | INI + env overrides (gitea), koanf URI providers env/file (signoz), typed factories + XML/JSON (jellyfin), kong CLI flags (crossplane) | all |
| Compose V2 naming | `compose.yaml` not `docker-compose.yml`; per-stack full isolation, no shared bases | awesome-compose |
| Edge delivery | Content-hashed immutable assets, CSP-hashed inline scripts, cookie (not localStorage) theme for SSR readability, island hydration | cloudflare-blog |
| Scheduled work | CronOperation CRD + robfig/cron (crossplane), `gocron` (signoz), custom TaskManager (jellyfin), DB-backed webhook task queue with retries (gitea) | 4 repos |

## Testing Approaches
- **Co-located unit tests** — all Go repos (`*_test.go` next to source); `go-cmp` (crossplane), testify + `<subsystem>test/` mock packages (signoz)
- **Fixture-based integration** — gitea: YAML fixtures loaded into SQLite per suite (`models/fixtures/*.yml`); migration tests: load fixture → run migration → assert
- **E2E on real clusters** — crossplane: `sigs.k8s.io/e2e-framework` + kind
- **Polyglot test stack** — signoz: Go unit + Python/pytest integration (dockerized fixtures for ClickHouse/Postgres/Keycloak/maildev, seeder container, golden files) + Playwright browser E2E
- **Fuzzing** — crossplane: OSS-Fuzz integration, external fuzzing audit
- **Health endpoint tests** — awesome-compose: chai-http against live app `/healthz`
- **Gaps**: jellyfin tests not visible in extraction; awesome-compose has no CI files

## Deployment & Production
- **Helm as primary vehicle, CRDs self-managed** — crossplane (`cluster/charts/`, initializer owns CRDs)
- **Multi-arch Docker + rootless variants** — gitea, signoz
- **Init-system breadth** — gitea ships systemd/supervisor/launchd/rc.d units
- **Operational self-healing CLI** — gitea `doctor` (fixes hooks, authorized_keys, DB consistency), `contrib/upgrade.sh`
- **Backup-before-migrate** — jellyfin full-system backup with manifest; migrations run pre-startup
- **Graceful shutdown/restart** — gitea signal-based with connection draining and socket inheritance
- **Observability exports** — Prometheus metrics (crossplane per-component `*_metrics.go` files, gitea `/metrics`), OTel tracing (crossplane, signoz); jellyfin has none visible
- **Edge resilience** — cloudflare-blog: feature detection before use, timeout-based UI degradation, cache-safe retry URLs

## Open Questions (for reviewer)
1. **CRD lifecycle**: Helm-managed vs self-managed initializer (crossplane's approach) — adopt which for our operators?
2. **Rate limiting layer**: middleware QoS (gitea) vs circuit breaker + token bucket at reconciler level (crossplane) — different layers; do we need both?
3. **Migration rollback**: all repos are forward-only; jellyfin compensates with backup-before-migrate. Adopt backup requirement?
4. **Log shipping**: file-based (awesome-compose ELK demo) vs stdout/log-driver — file-based explicitly flagged as demo-only; confirm stdout as standard.
5. **Embedded vs external observability services**: signoz embeds Prometheus/Alertmanager as libraries — acceptable pattern or prefer sidecars?
6. **Distributed lock backend**: memory vs Redis selection (gitea) — standardize on Redis-only or keep single-node fallback?
7. **Missing source**: chaos-engineering content was never extracted (Cloudflare block) — re-fetch before treating this doc as complete for incident-response/chaos coverage.
