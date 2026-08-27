# Role Definitions — DRAFT (Awaiting Approval)

> Sources: SWEBOK v4, IEEE/ACM, LinkedIn/levels.fyi job descriptions, tech company role guides
> Date: 2026-08-16
> Status: DRAFT — user must review and approve before knowledge acquisition begins

## What Existing Skills Already Cover (DON'T repeat in roles)

Our `/implementation`, `/debug_tool`, `/reviewer`, `/precommit`, `/architecture` skills already handle:
- Programming fundamentals, data structures, algorithms
- Git workflow, version control
- Testing principles (TDD, unit/integration)
- Code review process
- Debugging methodology (hypothesis-driven)
- CI/CD awareness
- Agile process (skill workflows ARE the process)
- Basic HTTP/REST knowledge
- Quality gates, pre-commit checks

**Roles only add DOMAIN KNOWLEDGE — the judgment and expertise a specialist brings.**

---

## Role Definitions

### 1. Backend Engineer

**Domain knowledge (what a generic coder lacks):**
- Connection pooling mechanics (pool size = request_rate x avg_hold_time)
- Cache patterns: cache-aside, read-through, write-through, stampede prevention
- Idempotency: idempotency keys for POST, at-least-once delivery implications
- Pagination: cursor-based vs offset (and why offset breaks at scale)
- Rate limiting algorithms: token bucket, sliding window
- Distributed patterns: saga, circuit breaker, bulkhead, retry with jitter
- Transaction isolation levels and real-world tradeoffs
- Query plan reading (EXPLAIN), index selection (B-tree vs hash vs GIN)
- Auth architecture: OAuth 2.0 flows, JWT rotation, RBAC vs ABAC
- Observability: RED method, structured logging with correlation IDs

**Core duties:**
- Design/implement APIs (REST, GraphQL, gRPC)
- Database schema design and migrations
- Business logic and domain models
- Third-party service integration
- Performance optimization (queries, caching, throughput)

**Invokes:** DBA (after schema), Security (after auth), DevOps (after deployment config)

---

### 2. Frontend Developer

**Domain knowledge:**
- Browser rendering pipeline: DOM > CSSOM > layout > paint > composite
- JS event loop, microtasks vs macrotasks, requestAnimationFrame
- Bundle splitting, tree shaking, critical rendering path
- Core Web Vitals: LCP < 2.5s, INP < 200ms, CLS < 0.1
- Accessibility: ARIA roles, semantic HTML, keyboard navigation, screen readers
- State management: local vs global, server state vs client state, optimistic updates
- Web Workers for CPU-intensive tasks (>50ms = main thread blocking)

**Core duties:**
- Build interactive UIs with component frameworks
- Responsive layouts across devices
- API integration (consumption side)
- Load/runtime performance optimization
- Client-side routing, forms, error boundaries

**Invokes:** Backend (for API contracts), Security (for XSS/CSRF review)

---

### 3. iOS Developer

**Domain knowledge:**
- ARC: strong/weak/unowned references, retain cycle detection
- UIKit lifecycle (viewDidLoad to viewDidDisappear) and SwiftUI declarative paradigm
- GCD and Swift Concurrency (async/await, actors, structured concurrency)
- Core Data: NSManagedObjectContext, merge policies, lightweight migrations
- App Store review guidelines, code signing, provisioning profiles
- Push notifications (APNs), background modes, silent push
- Keychain Services for secure storage
- Auto Layout constraint system, size classes, trait collections

**Core duties:**
- Build native iOS apps (Swift/SwiftUI)
- Manage app lifecycle, navigation, data persistence
- Platform-specific UX (haptics, gestures, system integration)
- App Store submission, TestFlight

**Invokes:** Backend (for API contracts), Security (for secure storage review)

---

### 4. Android Developer

**Domain knowledge:**
- Activity/Fragment lifecycle, ViewModel survival across config changes
- Jetpack Compose: recomposition optimization, side effects
- Kotlin Coroutines and Flow, structured concurrency
- Memory model: GC, memory leaks from static Context references
- Gradle: build variants, flavors, ProGuard/R8 shrinking
- Content Providers, BroadcastReceivers, Services (foreground/bound/started)
- Room, DataStore, WorkManager for deferred work
- Material Design 3, adaptive layouts for tablets/foldables

**Core duties:**
- Build native Android apps (Kotlin/Compose)
- Handle device fragmentation (OS versions, screens, hardware)
- Battery and memory optimization
- Play Store releases, staged rollouts

**Invokes:** Backend (for API contracts), Security (for secure storage)

---

### 5. DBA / Data Engineer

**Domain knowledge:**
- Query plan optimization at server level, buffer pool tuning
- Replication: logical vs physical, leader-follower, quorum
- Point-in-time recovery, pg_stat_statements, slow query analysis
- Lock contention diagnosis, vacuum tuning, connection limits
- ETL/ELT pipeline design, CDC (change data capture)
- Data warehouse modeling: star schema, snowflake schema
- Data lake: partitioning, file formats (Parquet, ORC, Avro)
- Airflow DAGs, data quality frameworks (Great Expectations)
- Schema registry for streaming data

**Core duties:**
- DBA: database health, performance tuning, backup/restore, capacity planning
- Data Eng: build/maintain pipelines, transform data, manage lineage

**Invokes:** Backend (for app-level query review), SRE (for database monitoring)

---

### 6. DevOps / Cloud Engineer

**Domain knowledge:**
- Terraform: state management, module composition, drift detection
- Kubernetes: Pod/Deployment/StatefulSet/DaemonSet, HPA/VPA, network policies
- CI/CD: build caching, artifact management, canary/blue-green/rolling deploys
- Cloud mental models: managed vs self-hosted, serverless cost, reserved vs spot
- Networking: VPCs, subnets, security groups, LB algorithms, DNS records
- Secret management: Vault, rotation strategies
- Observability infra: Prometheus/Grafana, log aggregation, alert design

**Core duties:**
- Provision/manage cloud infrastructure
- Build/maintain CI/CD pipelines
- Container orchestration
- Infrastructure security and compliance
- Cost optimization

**Invokes:** Security (for infra hardening), SRE (for reliability review)

---

### 7. Security Engineer

**Domain knowledge:**
- OWASP Top 10 mechanics (not just the list — HOW each attack works)
- Cryptography applied: bcrypt/argon2/scrypt, envelope encryption, TLS handshake
- Threat modeling: STRIDE, DREAD, attack trees
- Security architecture: zero-trust, defense in depth, least privilege
- Compliance: SOC 2 controls, GDPR technical requirements, PCI-DSS
- Supply chain: SBOM, dependency scanning, signed builds
- Forensics: log analysis for intrusion detection, incident response playbooks

**Core duties:**
- Security audits and pen tests
- Auth architecture design
- Security monitoring and alerting
- Incident response
- Policy definition and enforcement

**Invokes:** evaluates ALL other roles' output (security is cross-cutting)

---

### 8. Data Scientist

**Domain knowledge:**
- Statistical methods: hypothesis testing, A/B test design (power analysis, sequential testing)
- Feature engineering: encoding, missing data, scaling, dimensionality reduction
- Model selection: bias-variance tradeoff, cross-validation, regularization
- Causal inference: diff-in-diff, instrumental variables, propensity scores
- Experimental design: randomization, stratification, novelty effects
- Data visualization: choosing chart types, avoiding misleading visualizations

**Core duties:**
- Analyze data to answer business questions
- Design and analyze A/B tests
- Build predictive models (prototypes)
- Communicate findings to non-technical stakeholders
- Define metrics and KPIs

**Invokes:** ML Engineer (to productionize), Data Engineer (for pipeline needs)

---

### 9. ML Engineer

**Domain knowledge:**
- Model serving: batch vs real-time inference, model versioning, A/B in production
- MLOps: experiment tracking (MLflow, W&B), model registry, feature stores
- Optimization: quantization, pruning, distillation, ONNX, TensorRT
- Training infra: distributed training, GPU memory, mixed-precision
- Feature pipelines: online vs offline, freshness, point-in-time correctness
- Monitoring: data drift, concept drift, model degradation alerting
- LLM-specific: RAG, fine-tuning vs ICL, token management, embeddings

**Core duties:**
- Productionize ML models with reliable serving
- Build/maintain training and inference pipelines
- Optimize model performance (latency, throughput, cost)
- Monitor model quality in production
- Manage GPU/TPU infrastructure

**Invokes:** Data Scientist (for model development), DevOps (for infra), Backend (for API serving)

---

### 10. System Architect

**Domain knowledge:**
- Quality attribute tradeoffs: scalability vs consistency vs latency vs cost
- Architecture Decision Records (ADRs)
- Integration patterns: sync vs async, choreography vs orchestration, API gateway
- Domain-Driven Design: bounded contexts, context mapping, anti-corruption layers
- Capacity planning: Little's Law, Universal Scalability Law
- Build vs buy evaluation, migration cost estimation, lock-in risk
- Non-functional requirements: quantified availability (99.9% vs 99.99%), latency budgets

**Core duties:**
- Define system boundaries and integration patterns
- Technology selection with documented tradeoffs
- Guide teams on architectural constraints
- Review designs for scalability, security, maintainability

**Invokes:** evaluates ALL roles' architectural decisions

---

### 11. QA Engineer

**Domain knowledge:**
- Test strategy: risk-based testing, test pyramid ratios, testing quadrants
- Automation architecture: page object model, screenplay pattern, test data management
- Non-functional testing: load testing (saturation points), chaos engineering, accessibility audits
- Exploratory testing: session-based, SFDIPOT heuristic, bug taxonomies
- Contract testing: Pact, consumer-driven contracts for microservices
- Mobile testing: device farms, gesture simulation, network condition simulation
- Mutation testing (beyond line coverage)

**Core duties:**
- Design test strategies and test plans
- Build/maintain automated test suites
- Exploratory testing and edge case discovery
- Validate non-functional requirements

**Invokes:** evaluates ALL roles' test coverage and quality

---

### 12. SRE (Site Reliability Engineer)

**Domain knowledge:**
- SLO/SLI/SLA design: meaningful SLIs, error budgets, error budget policies
- Incident management: incident commander, blameless postmortems, severity classification
- Toil identification: measuring toil %, automation ROI
- Capacity planning: load testing, growth forecasting, headroom calculation
- Reliability patterns: graceful degradation, load shedding, circuit breakers (operational view)
- On-call: escalation policies, runbook design, alert actionability
- Linux internals: process scheduling, memory management, network stack (for diagnosis)

**Core duties:**
- Define/maintain SLOs
- Build automation to reduce toil
- Incident response and postmortems
- Capacity planning and performance tuning
- On-call rotation

**Invokes:** DevOps (for infra changes), Backend (for app-level fixes)

---

### 13. Game Developer

**Domain knowledge:**
- Game loop: fixed vs variable timestep, frame rate independence, interpolation
- ECS: data-oriented design, cache-friendly layouts, archetype storage
- Graphics pipeline: shaders, draw call batching, GPU instancing, LOD
- Physics: collision detection (broad/narrow phase), rigid body, raycasting
- Multiplayer: client-side prediction, server reconciliation, lag compensation
- Memory: object pooling, arena allocators, avoiding GC pauses
- Platform optimization: console cert requirements, target FPS, thermal throttling

**Core duties:**
- Implement gameplay mechanics and systems
- Optimize for target frame rates
- Integrate art/animation/audio assets
- Build multiplayer networking
- Debug performance and physics issues

**Invokes:** Backend (for multiplayer servers), QA (for playtesting)

---

### 14. Embedded / IoT Developer

**Domain knowledge:**
- RTOS: preemptive vs cooperative scheduling, priority inversion, semaphores
- Hardware interfaces: I2C, SPI, UART, CAN bus, GPIO, ADC/DAC, PWM
- Memory constraints: 64-256KB RAM typical, static allocation, memory-mapped I/O
- Power management: sleep modes, wake sources, duty cycling, battery optimization
- Protocols: MQTT, CoAP, BLE, ZigBee, LoRa (range vs power vs bandwidth)
- Firmware updates: OTA architecture, bootloader design, firmware signing, rollback
- Interrupts: ISR design (keep short, defer work), priority, race conditions
- Cross-compilation: toolchains, linker scripts, JTAG/SWD debugging

**Core duties:**
- Write firmware for microcontrollers
- Interface with sensors, actuators, communication modules
- Optimize power consumption and memory usage
- Design communication protocols
- Debug hardware/software interaction

**Invokes:** Security (for firmware signing), Backend (for cloud integration)

---

## Roles Recommended for Merging/Modification

### API Developer > Merge into Backend
Too much overlap with Backend Engineer. Make it a specialization flag: `backend.specialization: api`. Unique knowledge (OpenAPI authoring, SDK generation, versioning strategies) becomes a sub-section of Backend.

### Tech Lead > Modifier Role
Not a technical domain — it's judgment and leadership. Instead of standalone role, make it a modifier that enhances other roles with:
- Technical debt quantification
- Estimation and risk assessment
- Knowing when NOT to build
- Cross-team coordination awareness

---

## Overlap Summary

```
High overlap (consider merging): API<>Backend, SRE<>DevOps, iOS<>Android
Medium overlap (share knowledge): Backend<>DBA, DevOps<>Security
Cross-cutting (evaluate everyone): Security, Architect, QA
```

---

## Phasing Recommendation

**Phase 1 (6 core roles):** Backend, Frontend, DBA, Security, DevOps, Mobile (iOS+Android combined)
**Phase 2 (5 specialist roles):** Data Scientist, ML Engineer, Architect, QA, SRE
**Phase 3 (3 niche roles):** Game Dev, Embedded/IoT, remaining specializations

---

## Approval Checklist

- [ ] Role list OK? (add/remove/merge any?)
- [ ] Domain knowledge per role correct? (anything missing or wrong?)
- [ ] Merge API into Backend?
- [ ] Tech Lead as modifier instead of standalone?
- [ ] Phase 1 starting set (6 roles)?
