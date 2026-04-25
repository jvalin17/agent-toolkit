# System Architecture

Decisions for scaling, reliability, observability, and team workflow. Relevant for any system beyond prototype stage or with multiple developers.

## Inputs

Read `requirements/<name>.md` and extract:
- **Non-functional requirements** — scale targets, uptime SLA, latency budgets
- **Team context** — team size, experience levels, on-call expectations
- **Deployment environment** — cloud provider, on-prem, hybrid, budget

Also read the Quick Architecture from `architecture/<name>.md` for the chosen architecture pattern and tech stack.

---

## Part 1: Scaling & Reliability

### Decision 1: Current Scale Stage

**Context:** Right-size infrastructure to the actual stage. The most common mistake is over-engineering for scale that may never come.

**Options:**

| | Stage A: Prototype / MVP | Stage B: Growing (100-10K users) | Stage C: Scale (10K-1M users) | Stage D: Large Scale (1M+) |
|---|---------|---------|---------|---------|
| What | Single server, minimal infra | Reliability, basic redundancy | Horizontal scaling, distributed systems | Global distribution, sharding |
| Infra | Single VPS or PaaS (Heroku, Railway, Fly.io) | Managed services, load balancer, read replica | Multi-AZ, auto-scaling, message queues | Multi-region, edge computing |
| Cost | $0-50/mo | $50-500/mo | $500-5,000/mo | $5,000+/mo |
| SOLID/DRY check | ✅ KISS — simplest that works | ✅ Add complexity as needed | ⚠️ Justified by scale | ⚠️ Must be well-separated |

**Consequence:** This decision gates every other decision. Do not design Stage C infrastructure for a Stage A product.

---

### Decision 2: Next Bottleneck & Component

**Context:** What breaks first as load increases, and what to add when it does. Depends on current stage (Decision 1).

| Bottleneck | Symptom | Component to Add | Cheap Alternative |
|-----------|---------|-----------------|-------------------|
| DB on same server | Slow queries + slow app | Separate DB server | SQLite WAL mode |
| Connection limits | Pool exhaustion, timeouts | Connection pooler (PgBouncer) | ORM built-in pooling |
| App server overloaded | High CPU, request queuing | Load balancer + 2nd server | Vertical scaling |
| Slow reads | High query latency | Read replica or cache (Redis) | Application-level cache |
| Background job backlog | Queue growth, timeouts | Job queue (Redis, SQS) | In-process queue (BullMQ) |
| Search performance | Slow text queries | Search engine (Meilisearch) | PostgreSQL full-text search |

**Do not add components preemptively.** Each adds operational complexity. Only add when the bottleneck is real or imminent.

---

### Decision 3: Failure Modes & Recovery

**Context:** What happens when things break, and how the system recovers.

**Failure mode table** (fill in for each component in the architecture):

| Component | Failure Mode | User Impact | Mitigation |
|-----------|-------------|-------------|------------|
| App server | Process crash | 502 errors | Auto-restart, multiple instances |
| Database | Connection refused | All reads/writes fail | Retry with backoff, read replica |
| Cache | Memory full / crash | Slower responses | Graceful degradation (app works without cache) |
| External API | Timeout / 5xx | Feature unavailable | Circuit breaker, cached fallback |

**Recovery options:**

| | Option A: Manual | Option B: Automated Restart | Option C: Self-Healing |
|---|---------|---------|---------|
| What | Ops team investigates and fixes | Process managers, container restarts | Automated detection + remediation |
| Best for | Early stage, rare failures | Production systems | High-availability (99.99%+) |
| Trade-off | Slow, human bottleneck | May crash-loop | Complex automation |
| SOLID/DRY check | ✅ Simple | ✅ Standard practice | ⚠️ Must be well-tested |

**Backup basics:** Automated daily DB backups, test restore regularly, define RTO/RPO based on requirements.

---

## Part 2: Observability

### Decision 4: Logging Strategy

**Context:** What to log, where, and how. Foundational observability decision.

**Options:**

| | Option A: Unstructured | Option B: Structured (JSON) | Option C: Centralized (ELK, Datadog) |
|---|---------|---------|---------|
| What | console.log/print to stdout | JSON logs with consistent fields | Aggregated to searchable platform |
| Best for | Local development | Production systems | Multi-service, team debugging |
| Trade-off | Unparseable at scale | Requires log library setup | Cost at volume |
| Cost | Free | Free | $10-500/mo |

**What to log:** Request ID, timestamp, level, service, action, duration, errors. **Never log:** secrets, passwords, PII.

---

### Decision 5: Metrics & Monitoring

**Context:** What to measure. Depends on logging (Decision 4).

**Options:**

| | Option A: Application Only | Option B: App + Infrastructure | Option C: Full Stack |
|---|---------|---------|---------|
| What | RED metrics (Rate, Errors, Duration) | Add CPU, memory, disk, network | Metrics + logs + traces + profiling |
| Best for | Small apps | Production systems | Distributed systems |
| Cost | Free (Prometheus + Grafana) | Moderate | $100-1,000+/mo |

**Key metrics (RED):** Rate (req/sec), Errors (error %), Duration (p50/p95/p99).

---

### Decision 6: Tracing & Alerting

**Tracing** (skip for monoliths):

| | Option A: Request ID Correlation | Option B: Full Distributed Tracing (OpenTelemetry) |
|---|---------|---------|
| What | Pass request ID through services, correlate in logs | Instrument with spans, visualize call graphs |
| Best for | 2-5 services | Microservices, complex meshes |
| Cost | Free (just a header) | Free (Jaeger) to paid |

**Alerting:**

| | Option A: Threshold-Based | Option B: SLO-Based |
|---|---------|---------|
| What | Alert when metric crosses threshold (error rate > 5%) | Alert when error budget consumed too fast |
| Best for | Most systems | Teams with defined SLAs |
| Trade-off | Noisy if thresholds wrong | Requires SLO/error budget tracking |

**Alert principles:** Every alert must be actionable. Define severity: P1 (wake someone), P2 (fix today), P3 (this week). Start with few critical alerts.

---

### Decision 7: Health Checks

**Options:**

| | Option A: Simple Ping | Option B: Deep Health | Option C: Liveness + Readiness |
|---|---------|---------|---------|
| What | /health returns 200 if running | Checks DB, cache, dependencies | Separate liveness and readiness endpoints |
| Best for | Simple deployments | Multi-dependency services | Kubernetes, orchestrators |

Health checks should be fast (< 1s) and unauthenticated.

---

## Part 3: Team Workflow

Only relevant for multi-developer teams. Skip for solo projects.

### Decision 8: Branching & Code Review

**Branching:**

| | Option A: Trunk-Based | Option B: GitHub Flow | Option C: Git Flow |
|---|---------|---------|---------|
| What | Commits to main, short branches (< 1 day) | Feature branches, PR to merge | develop + main + release branches |
| Best for | Strong CI, continuous deployment | Most teams | Scheduled releases |

**Code review:** 1 approver (small teams) vs 2 approvers (critical systems) vs pair programming (no separate review). Checklist: correctness, tests, security, readability, conventions.

---

### Decision 9: Ownership, ADRs & Onboarding

- **Ownership:** Strong (module owners) vs collective (anyone changes anything). Strong scales better.
- **ADRs:** Document decisions in `docs/adr/` with: Status, Context, Decision, Consequences.
- **Onboarding:** Setup instructions, architecture overview, first task guide. Keep it current.

---

## Decision Format Reference

Each decision above follows the standard format from the base SKILL.md. For guardrails (G-ARCH-1 through G-ARCH-4, G1-G9), see `shared/guardrails.md` — they are not duplicated here.
