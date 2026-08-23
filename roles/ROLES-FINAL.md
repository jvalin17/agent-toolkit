# Roles — FINAL (Approved 2026-08-16)

> 19 roles locked in. Ready for knowledge acquisition.
> Sources: SWEBOK v4, IEEE/ACM, FAANG + startup role research, user review
> Principle: Roles add DOMAIN KNOWLEDGE only. Workflow/process lives in skills.

## Role List

| # | Role | Category | Primary Focus |
|---|------|----------|---------------|
| 1 | Backend Engineer | Core | APIs, server logic, auth, caching, integrations |
| 2 | Frontend Developer | Core | UI, components, accessibility, Web Vitals, state |
| 3 | iOS Developer | Mobile | Native iOS, Swift/SwiftUI, ARC, App Store |
| 4 | Android Developer | Mobile | Native Android, Kotlin/Compose, lifecycle, Play Store |
| 5 | DBA | Data | Database server tuning, replication, indexes, backup, query plans |
| 6 | Data Engineer | Data | Pipelines, ETL/ELT, warehouses, streaming, data quality |
| 7 | Data Scientist | Data | Statistics, A/B tests, experiments, model prototypes, metrics |
| 8 | AI/ML Engineer | AI/ML | Model training/serving, MLOps, RAG, LLMs, embeddings, fine-tuning |
| 9 | Infrastructure Engineer | Infra | IaC, K8s, CI/CD, cloud, monitoring, SLOs, incident response |
| 10 | Security Engineer | Cross-cutting | OWASP, auth design, threat modeling, dependencies, compliance |
| 11 | Production Engineer | Cross-cutting | Run app, verify behavior, performance, bug reproduction, smoke tests |
| 12 | QA Engineer | Cross-cutting | Test strategy, environments, automated suites, regression, E2E, edge cases |
| 13 | System Architect | Cross-cutting | System design at all scales, ADRs, capacity planning, DDD, integration patterns |
| 14 | Code Health Engineer | Cross-cutting | Refactoring safety, tech debt, dependency health, complexity, regressions |
| 15 | Requirements Engineer | Cross-cutting | Spec-to-code mapping, gap detection, change propagation, scope tracking |
| 16 | Research Engineer | Cross-cutting | Modern patterns, tech evaluation, papers, blogs, competitors, tooling research |
| 17 | Game Developer | Specialized | Game loop, ECS, physics, graphics, multiplayer netcode, performance |
| 18 | Embedded/IoT Developer | Specialized | Firmware, RTOS, hardware interfaces, power management, OTA updates |

## Role Interactions

### Who invokes whom (deterministic, defined in role config)

```
Backend Engineer
  → after schema: DBA
  → after auth: Security Engineer
  → after deployment config: Infrastructure Engineer
  → for evaluation: Security, QA

Frontend Developer
  → for API contracts: Backend Engineer
  → for evaluation: Security (XSS/CSRF), QA, Production Engineer

iOS Developer / Android Developer
  → for API contracts: Backend Engineer
  → for evaluation: Security, QA, Production Engineer

DBA
  → for app-level review: Backend Engineer
  → for monitoring: Infrastructure Engineer

Data Engineer
  → for source data: DBA
  → for consumers: Data Scientist, AI/ML Engineer

Data Scientist
  → to productionize: AI/ML Engineer
  → for pipeline needs: Data Engineer

AI/ML Engineer
  → for model dev: Data Scientist
  → for infra: Infrastructure Engineer
  → for API serving: Backend Engineer

Infrastructure Engineer
  → for hardening: Security Engineer
  → for evaluation: Security, QA

Security Engineer
  → evaluates: ALL roles (cross-cutting)
  → for dependency analysis: scans all dependencies

Production Engineer
  → runs and verifies: ALL roles' output
  → reports to: Code Health (regressions), Requirements (completeness)

QA Engineer
  → designs tests for: ALL roles
  → creates environments for: Production Engineer
  → reports gaps to: Code Health Engineer

System Architect
  → evaluates: ALL roles' architectural decisions
  → guides: Backend, Infrastructure, Data Engineer

Code Health Engineer
  → monitors: ALL roles' code quality
  → reports to: System Architect (structural issues)

Requirements Engineer
  → tracks: ALL roles' spec compliance
  → reports gaps to: relevant role + System Architect
  → owns: i18n/localization strategy (which languages, what's translated, RTL support)
  → owns: technology/language/tool selection — consults relevant engineers, documents decisions
  → consults: Frontend (UI framework), Backend (server framework), iOS/Android (native vs cross-platform), Infrastructure (cloud provider), DBA (database), Research Engineer (modern options)

Research Engineer
  → feeds knowledge to: ALL roles
  → sources: papers, blogs, company tech blogs, conferences, repos
  → evaluates: technology decisions for any role
```

### Cross-cutting roles (evaluate everyone)

| Role | What it checks across all roles |
|------|-------------------------------|
| Security Engineer | Vulnerabilities, auth, secrets, dependencies, compliance |
| QA Engineer | Test coverage, test quality, edge cases, environments |
| Production Engineer | Does it actually work? Performance? Responsiveness? |
| Code Health Engineer | Code quality, complexity, regressions, tech debt |
| Requirements Engineer | Is the spec fully implemented? Any drift? |
| Research Engineer | Are we using modern, appropriate approaches? |
| System Architect | Is the architecture sound at every level? |

## Research Engineer — Continuous Learning Scope

The Research Engineer is the system's **learning engine**. It doesn't just research on demand — it continuously ingests knowledge that improves all other roles.

### Knowledge Sources

| Source | What to Extract | Frequency |
|--------|----------------|-----------|
| **Academic papers** (arxiv, IEEE, ACM) | New algorithms, approaches, benchmarks | Weekly |
| **Company engineering blogs** | How Netflix/Uber/Stripe/Meta solve problems at scale | Weekly |
| Netflix Tech Blog | Streaming, microservices, chaos engineering | |
| Uber Engineering | Marketplace, maps, real-time systems | |
| Stripe Blog | Payment systems, API design, developer experience | |
| Meta Engineering | Infrastructure, AI/ML, mobile at scale | |
| Google AI Blog | ML research, production AI systems | |
| Vercel Blog | Frontend, edge computing, serverless | |
| Cloudflare Blog | Networking, security, edge, Workers | |
| **Developer blogs** (Medium, dev.to) | Practical tutorials, pattern comparisons | Ongoing |
| **Hacker News top posts** | Industry trends, tool launches, debates | Daily |
| **Framework changelogs** | What's new in React, Next.js, Swift, Kotlin, etc. | On release |
| **Conference talk summaries** | KubeCon, WWDC, Google I/O, re:Invent, JSConf | Per event |
| **Open-source repo analysis** | How top repos structure code, handle edge cases | Per role |

### Potential Split (if scope becomes too large)

| Sub-role | Focus |
|----------|-------|
| Research Engineer (Tech) | Frameworks, libraries, coding patterns, architecture |
| Research Engineer (Industry) | Papers, company blogs, conference talks, trends |
| Research Engineer (Market) | Competitors, product analysis, feature comparison |

Split only when `_synthesis.md` becomes too large or unfocused to be useful.

## Manager Guardrail (applies to all roles)

5 principles injected alongside active roles:
1. **QUALITY** — check anti-patterns before implementing
2. **SCOPE** — solve exactly what was asked
3. **DEPENDENCIES** — check all applicable roles' guidance
4. **RISK** — address flagged risks, don't defer
5. **ESCALATION** — follow user instructions when role guidance conflicts

## Next Steps

1. Update architecture doc (v4) with final 18 roles
2. Begin knowledge acquisition pipeline:
   a. Curate repos per role (repos.json)
   b. Build indexer (Python + LLM)
   c. Index starter roles first (Backend, Frontend, Security, DBA)
   d. Synthesize knowledge per role
3. Build detect_role.py
4. Integrate into session_init.py and route_to_skill.py
