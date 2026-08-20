# Role Coverage Review — What Each Role Covers

> Status: DRAFT — review and finalize before implementation
> Date: 2026-08-16
> Purpose: Full scope of what each role researches, evaluates, builds, and maintains

---

## 1. Backend Engineer

**Builds:**
- REST/GraphQL/gRPC APIs
- Database schemas, migrations, seed data
- Business logic, domain models, service layer
- Authentication/authorization systems (OAuth, JWT, sessions)
- Background jobs, task queues, scheduled tasks
- Webhook integrations (sending and receiving)
- File upload/download handling
- Email/SMS/notification sending
- Payment integration wiring (Stripe, payment gateways)
- Search integration (Elasticsearch, Algolia, full-text)
- Caching layers (Redis, Memcached, in-memory)
- WebSocket/real-time connections (server side)
- Multi-tenancy architecture
- API rate limiting and throttling
- Data validation and serialization
- Error handling and structured error responses
- Logging, correlation IDs, request tracing

**Evaluates:**
- Connection pooling configuration
- Query performance (EXPLAIN plans, N+1 detection)
- Cache hit rates and invalidation strategies
- API idempotency
- Transaction isolation tradeoffs
- Distributed patterns (saga, circuit breaker, retry with jitter)

**Does NOT cover:** UI rendering, native mobile, infrastructure provisioning, database server tuning (that's DBA)

---

## 2. Frontend Developer

**Builds:**
- Component-based UIs (React, Vue, Svelte, Angular)
- Responsive layouts (mobile, tablet, desktop)
- Client-side routing and navigation
- Forms, validation, error states
- Data fetching, caching, optimistic updates
- State management (local, global, server state, URL state)
- Animations and transitions
- Dark mode, theming, design system integration
- Accessibility (ARIA, keyboard nav, screen reader support)
- Progressive Web Apps (service workers, offline support)
- Real-time UI updates (WebSocket client, SSE)
- File upload UIs (drag-drop, progress, preview)
- Charts, data visualization, dashboards
- Internationalization (i18n) and localization
- SEO (meta tags, structured data, SSR/SSG)
- Error boundaries, loading states, skeleton screens
- Browser storage (localStorage, IndexedDB, cookies)

**Evaluates:**
- Core Web Vitals (LCP, INP, CLS)
- Bundle size, code splitting, tree shaking
- Main thread blocking (>50ms tasks)
- Lazy loading strategy (what to defer, what not to)
- Image optimization (format, sizing, loading strategy)
- Render performance (layout thrashing, repaints)
- Cross-browser compatibility

**Does NOT cover:** Server-side logic, database, native mobile, infrastructure

---

## 3. iOS Developer

**Builds:**
- Native iOS apps (Swift, SwiftUI, UIKit)
- Navigation patterns (NavigationStack, TabView, sheets)
- Data persistence (Core Data, SwiftData, UserDefaults, Keychain)
- Networking layer (URLSession, async/await)
- Push notifications (APNs, local notifications)
- Background processing (BGTaskScheduler)
- Camera, photos, media capture
- Location services, maps
- In-app purchases, subscriptions (StoreKit 2)
- Widgets (WidgetKit), App Clips
- Share extensions, app extensions
- Biometric auth (Face ID, Touch ID)
- Haptic feedback, gestures
- Accessibility (VoiceOver, Dynamic Type)
- Deep linking, universal links
- App Store screenshots, metadata, review handling

**Evaluates:**
- Memory management (retain cycles, leak detection with Instruments)
- App lifecycle handling (background/foreground transitions)
- Battery and CPU usage
- App size optimization
- Launch time optimization
- Crash reporting and symbolication

**Does NOT cover:** Android, web frontend, server-side, infrastructure

---

## 4. Android Developer

**Builds:**
- Native Android apps (Kotlin, Jetpack Compose)
- Navigation (Navigation Component, deep links)
- Data persistence (Room, DataStore, SharedPreferences)
- Networking (Retrofit, Ktor, OkHttp)
- Push notifications (FCM)
- Background work (WorkManager, foreground services)
- Camera, media, file handling
- Location, maps (Google Maps SDK)
- In-app billing (Google Play Billing Library)
- Widgets (Glance), app shortcuts
- Biometric authentication
- Material Design 3 components
- Accessibility (TalkBack, content descriptions)
- Multi-device support (tablets, foldables, Wear OS, Android Auto)
- Play Store listing, staged rollouts, in-app updates

**Evaluates:**
- Memory leaks (LeakCanary, profiler)
- Activity/Fragment lifecycle correctness
- Battery drain, Doze mode compatibility
- APK/AAB size optimization
- Startup time (cold/warm/hot start)
- Device fragmentation coverage
- ProGuard/R8 configuration

**Does NOT cover:** iOS, web frontend, server-side, infrastructure

---

## 5. DBA (Database Administrator)

**Builds/Configures:**
- Database server setup and configuration
- Replication topology (leader-follower, multi-leader, quorum)
- Backup and restore procedures (PITR, snapshots)
- Connection pooling config (PgBouncer, ProxySQL)
- Index strategy (B-tree, hash, GIN, GiST, partial, covering)
- Partitioning (range, list, hash)
- Sharding strategy and configuration
- Access control and database-level security (roles, permissions, row-level security)
- Vacuum/maintenance schedules (PostgreSQL)
- Query performance tuning at server level

**Evaluates:**
- Query plans (EXPLAIN ANALYZE, pg_stat_statements)
- Slow query logs, lock contention
- Buffer pool hit rates, cache effectiveness
- Replication lag, failover readiness
- Storage growth and capacity planning
- Connection utilization and limits
- Index usage and bloat

**Does NOT cover:** Application-level code, data pipelines (that's Data Engineer), API design, infrastructure provisioning

---

## 6. Data Engineer

**Builds:**
- ETL/ELT pipelines (batch and streaming)
- Data warehouse schemas (star, snowflake, data vault)
- Data lake architecture (partitioning, file formats: Parquet, ORC, Avro)
- CDC (Change Data Capture) pipelines
- Orchestration (Airflow DAGs, Prefect, Dagster)
- Data quality checks (Great Expectations, dbt tests)
- Schema registry for streaming (Kafka, Avro)
- Data catalogs and lineage tracking
- Real-time streaming (Kafka, Kinesis, Flink)
- Data transformations (dbt, Spark, SQL)
- Data governance and access policies
- Analytics database setup (ClickHouse, BigQuery, Snowflake, Redshift)

**Evaluates:**
- Pipeline reliability and idempotency
- Data freshness and latency
- Schema evolution compatibility
- Storage costs and optimization
- Query performance in analytical databases
- Data quality metrics (completeness, accuracy, timeliness)

**Does NOT cover:** Database server tuning (that's DBA), ML model building (that's Data Scientist/ML Engineer), application code

---

## 7. Data Scientist

**Builds:**
- Statistical analyses and reports
- A/B test designs (power analysis, sample size, duration)
- Predictive models (prototypes, not production)
- Feature engineering pipelines (for model development)
- Data visualizations and dashboards
- Metric definitions and KPI frameworks
- Experiment analysis scripts
- Cohort analyses, funnel analyses
- Forecasting models (time series, growth)
- Recommendation algorithms (prototypes)
- Customer segmentation, clustering

**Evaluates:**
- Statistical significance and practical significance
- Bias-variance tradeoff in models
- Data leakage risks
- Experiment validity (novelty effects, network effects, selection bias)
- Metric trustworthiness (Simpson's paradox, confounders)
- Visualization accuracy (misleading charts, cherry-picked ranges)

**Does NOT cover:** Production ML systems (that's ML Engineer), data pipelines (that's Data Engineer), application code

---

## 8. AI/ML Engineer

**Builds:**
- Model training pipelines (distributed training, hyperparameter tuning)
- Model serving infrastructure (batch, real-time, streaming inference)
- Feature stores (online and offline)
- Experiment tracking (MLflow, W&B, Neptune)
- Model registry and versioning
- RAG systems (retrieval-augmented generation)
- LLM integration (API wrappers, prompt chains, agent systems)
- Fine-tuning pipelines (LoRA, QLoRA, full fine-tune)
- Embedding pipelines (text, image, multimodal)
- Vector databases setup (Pinecone, Weaviate, Qdrant, pgvector)
- Prompt engineering and optimization
- Guardrails for LLM outputs (content filtering, hallucination detection)
- Model optimization (quantization, pruning, distillation, ONNX)
- A/B testing for models in production
- GPU/TPU infrastructure management

**Evaluates:**
- Model accuracy, precision, recall, F1
- Inference latency and throughput
- Data drift and concept drift
- Token usage and API costs (for LLM systems)
- Model fairness and bias
- Training/serving skew
- Feature freshness and correctness

**Does NOT cover:** Statistical experiment design (Data Scientist), raw data pipelines (Data Engineer), application business logic

---

## 9. Infrastructure Engineer

**Builds:**
- Infrastructure as Code (Terraform, Pulumi, CloudFormation)
- Container orchestration (Kubernetes, ECS, Docker Compose)
- CI/CD pipelines (GitHub Actions, GitLab CI, Jenkins)
- Cloud infrastructure (AWS, GCP, Azure — VPCs, subnets, load balancers)
- DNS configuration, domain management
- SSL/TLS certificate management
- Secret management (Vault, AWS Secrets Manager)
- Monitoring stack (Prometheus, Grafana, Datadog)
- Log aggregation (ELK, Loki, CloudWatch)
- Alerting rules and escalation policies
- Auto-scaling configuration (HPA, VPA, ASG)
- Disaster recovery and backup automation
- Cost optimization (reserved instances, spot, right-sizing)
- Internal developer platform tools
- Service mesh (Istio, Linkerd)
- CDN configuration (CloudFront, Fastly)
- Database infrastructure provisioning (managed services)

**Evaluates:**
- Deployment strategies (canary, blue-green, rolling)
- Infrastructure drift
- SLO/SLI/SLA compliance
- Incident response readiness (runbooks, on-call)
- Toil measurement and automation ROI
- Cost per service/team
- Security posture of infrastructure
- Capacity planning and headroom

**Does NOT cover:** Application business logic, UI, database query tuning (DBA), security audit depth (Security Engineer)

---

## 10. Security Engineer

**Builds:**
- Auth architecture design (OAuth 2.0, OIDC, SAML)
- Input validation and sanitization libraries
- CSP headers, CORS policies, security headers
- Encryption at rest and in transit
- Secret rotation automation
- Security scanning integration (SAST, DAST, SCA in CI/CD)
- Dependency vulnerability scanning and remediation
- License compliance checking
- SBOM (Software Bill of Materials) generation
- Penetration testing scripts and tools
- Incident response playbooks
- Compliance evidence collection (SOC 2, GDPR, PCI-DSS, HIPAA)
- Network security rules (firewalls, WAF, DDoS protection)
- API security (rate limiting from security perspective, API key management)

**Evaluates:**
- OWASP Top 10 compliance (injection, broken auth, XSS, SSRF, etc.)
- Cryptographic strength (hashing algorithms, key sizes, protocols)
- Threat models (STRIDE, attack trees)
- Supply chain risks (transitive dependencies, typosquatting)
- Secrets in code/repos/logs
- Access control correctness (RBAC, ABAC, least privilege)
- Data exposure risks (PII in logs, error messages, APIs)
- Third-party integration security

**Does NOT cover:** Application feature development, infrastructure provisioning (Infra Engineer), performance optimization

---

## 11. Production Engineer

**Runs/Verifies:**
- Start app locally, click through all flows manually
- Hit API endpoints, verify responses and database state
- Test E2E flows across the stack (frontend → backend → database → external services)
- Reproduce user-reported bugs in real environments
- Verify deployment success (smoke tests, health checks)
- Check server logs, error traces, stack traces
- Monitor response times, identify slowness
- Memory profiling (leaks, excessive usage)
- Load testing (simulate concurrent users)
- Verify data migrations completed correctly
- Test edge cases in real environments (empty states, large datasets, timeouts)
- Verify email/SMS/notification delivery
- Test payment flows in sandbox/staging
- Cross-browser and cross-device testing
- Accessibility verification (screen reader, keyboard-only)
- Verify rollback procedures work

**Evaluates:**
- App responsiveness and perceived performance
- Error rates and error handling quality
- Data integrity after operations
- User experience quality (loading states, error states, empty states)
- Server resource usage under load
- Third-party service degradation impact
- Feature completeness against requirements

**Does NOT cover:** Writing application code (other roles do that), infrastructure provisioning, security audits

---

## 12. System Architect

**Designs:**
- System boundaries and service decomposition
- API contracts between services
- Data flow diagrams (how data moves through the system)
- Technology selection with documented tradeoffs (ADRs)
- Integration patterns (sync vs async, REST vs events, API gateway)
- Database selection (SQL vs NoSQL, when to use which)
- Caching strategy (what to cache, where, invalidation)
- Message queue / event bus architecture
- Multi-region / global architecture
- Microservices vs monolith decision
- Domain-Driven Design (bounded contexts, aggregates)
- Capacity planning (Little's Law, back-of-envelope calculations)
- Migration strategies (strangler fig, parallel run, big bang)
- Disaster recovery architecture
- Multi-tenancy architecture
- Authentication/authorization architecture (cross-service)
- Observability architecture (what to measure, where)

**Evaluates:**
- Scalability (single server → millions of users)
- Availability and reliability (99.9% vs 99.99%)
- Consistency models (strong vs eventual)
- Latency budgets per service
- Cost at scale
- Coupling between services
- Single points of failure
- Data residency and compliance implications
- Build vs buy decisions
- Lock-in risk with cloud providers/services
- Technical debt architectural impact

**Does NOT cover:** Writing application code, UI design, database server tuning, security in depth

---

## 13. Code Health Engineer

**Maintains:**
- Test suite health (flaky test detection and fixing)
- Test coverage gaps identification
- Dependency upgrades (major version bumps, breaking change analysis)
- Dead code detection and removal
- Code complexity monitoring (cyclomatic complexity, cognitive complexity)
- Refactoring safety (snapshot behavior before, verify after)
- Migration completeness (old patterns fully replaced)
- Documentation freshness (code comments match implementation)
- Linting rule management and enforcement
- Type safety improvements
- Import/export structure cleanup
- Circular dependency detection and resolution
- Build time optimization
- Bundle size tracking over time
- Performance regression detection

**Evaluates:**
- Blast radius of proposed changes
- Regression risk assessment
- Technical debt severity and urgency
- Codebase health metrics over time
- Safe refactoring strategies (expand-contract, strangler fig at code level)
- Whether a refactor is worth doing (cost vs benefit)
- Dependency health (abandoned packages, security, alternatives)

**Does NOT cover:** New feature development, infrastructure, security audits, UI design

---

## 14. Requirements Engineer

**Tracks:**
- Requirement-to-implementation mapping (every spec item → code location)
- Requirement-to-test mapping (every spec item → test coverage)
- Requirement changes and propagation (spec changed → update code, tests, docs)
- Feature completeness verification (all acceptance criteria met)
- Scope drift detection (implementation exceeds or misses spec)
- Requirement conflicts and ambiguities
- User story decomposition into technical tasks
- Acceptance criteria clarity and testability
- Non-functional requirement tracking (performance, accessibility, security targets)
- API contract adherence to spec
- Data model alignment with requirements
- Edge case identification from requirements analysis

**Owns: Technology & Language Selection**
- Consult relevant engineers before choosing tech stack (don't let LLM pick on its own)
- Frontend: which UI framework? (consult Frontend Developer + Research Engineer)
- Backend: which server framework/language? (consult Backend Engineer + Research Engineer)
- Mobile: native vs cross-platform? (consult iOS + Android Developers + Research Engineer)
- Database: SQL vs NoSQL, which engine? (consult DBA + Research Engineer)
- Cloud: which provider/services? (consult Infrastructure Engineer + Research Engineer)
- AI/ML: which models/frameworks? (consult AI/ML Engineer + Research Engineer)
- Document all decisions with rationale (ADR-style)

**Owns: Localization / i18n Strategy**
- Which languages to support (based on target markets)
- RTL layout requirements (Arabic, Hebrew, Persian, Urdu)
- Translation management approach (i18n libraries, translation files, services)
- CJK text rendering considerations
- Date/time/number/currency formatting per locale
- Content vs UI translation (what gets translated, what stays English)
- Consult: Frontend (UI i18n), iOS/Android (platform i18n APIs), Legal (language requirements per market)

**Evaluates:**
- Gaps between requirements and implementation
- Missing requirements (what the spec doesn't say but should)
- Over-implementation (built more than was asked for)
- Requirement quality (testable, unambiguous, complete)
- Impact analysis when requirements change
- Priority conflicts between requirements
- Technology selection rationale (was the right tool chosen for the job?)
- Localization coverage (all target languages implemented?)

**Does NOT cover:** Writing application code, architecture design, testing execution, infrastructure

---

## 15. Research Engineer

**Researches:**
- Modern UI/UX patterns and interactions
- New libraries, frameworks, tools (is this worth adopting?)
- How competitors implement similar features
- Market analysis for feature decisions
- Best coding patterns for specific problems
- Design system trends and component libraries
- New kinds of apps (PWA, micro-frontends, island architecture)
- Payment system options (Stripe vs Paddle vs LemonSqueezy vs custom)
- Monitoring and observability tools comparison
- Alerting system options and patterns
- Lightweight vs enterprise solutions (when to use which)
- Naive implementations vs production-ready (what's the gap?)
- Large-scale app patterns (how Netflix/Uber/Stripe does X)
- Small-scale app patterns (how indie hackers/startups do X efficiently)
- ML algorithms for specific use cases (which model fits this problem?)
- Cloud service comparisons (which provider/service for this use case?)
- Open-source alternatives to paid services
- Authentication providers comparison
- Database selection for specific use cases
- Performance optimization techniques (specific to technology)
- Accessibility compliance approaches
- Internationalization strategies
- Analytics and tracking approaches (privacy-respecting)
- SEO strategies for different app types
- Mobile development approaches (native vs cross-platform vs hybrid)
- Real-time communication options (WebSocket vs SSE vs polling vs WebRTC)
- File storage solutions (S3 vs R2 vs local vs CDN)
- Search solutions (Elasticsearch vs Algolia vs Meilisearch vs Typesense)
- Email delivery services and patterns
- Background job processing options
- API documentation tools and approaches
- Testing tools and frameworks comparison
- CI/CD tool evaluation
- Tooling for code quality (linters, formatters, type checkers)

**Evaluates:**
- Is this technology production-ready?
- What's the maintenance burden?
- Community size and activity
- Learning curve vs benefit
- Cost at different scales
- Lock-in risk
- Integration complexity with our existing stack
- Performance characteristics
- Security track record

**Does NOT cover:** Building the implementation (other roles do that), running production systems, security audits

---

## 16. Game Developer

**Builds:**
- Game loops (fixed/variable timestep)
- Gameplay mechanics and systems
- Physics integration (collision, rigid body, raycasting)
- Entity Component System (ECS) architecture
- Rendering pipeline integration (shaders, materials, lighting)
- Animation systems (skeletal, blend trees, state machines)
- Audio systems (spatial audio, music, SFX)
- Input handling (keyboard, mouse, gamepad, touch)
- UI systems (HUD, menus, inventory)
- Save/load systems (serialization, cloud saves)
- Multiplayer networking (client prediction, server reconciliation, lag compensation)
- Level/scene management and loading
- Asset pipeline (import, optimize, package)
- Particle systems and VFX
- AI/pathfinding (A*, navmesh, behavior trees)
- Procedural generation (terrain, dungeons, content)

**Evaluates:**
- Frame rate stability (30/60/120 FPS targets)
- Memory usage and GC pressure
- Draw call counts, GPU utilization
- Physics performance (broad/narrow phase optimization)
- Network latency impact on gameplay
- Platform certification requirements
- Load times and streaming

**Does NOT cover:** Web apps, enterprise software, data pipelines, infrastructure

---

## 17. Embedded / IoT Developer

**Builds:**
- Firmware for microcontrollers (C/C++, Rust, MicroPython)
- Hardware interface drivers (I2C, SPI, UART, CAN, GPIO)
- RTOS task scheduling and inter-task communication
- Sensor data acquisition and processing
- Actuator control systems
- Communication stacks (BLE, WiFi, LoRa, ZigBee, MQTT, CoAP)
- OTA firmware update systems
- Bootloader design
- Power management and battery optimization
- Interrupt service routines
- Watchdog timer configuration
- Flash storage management (wear leveling, filesystem)
- Device provisioning and identity management
- Edge computing and local ML inference
- Hardware abstraction layers
- Protocol bridges (sensor → cloud)

**Evaluates:**
- Power consumption per operation
- Memory usage (RAM and flash)
- Real-time guarantees (timing constraints)
- Hardware/software interaction bugs
- Communication reliability and range
- Firmware update safety (rollback, corruption protection)
- EMC/EMI compliance considerations
- Operating temperature range behavior
- Battery life projections

**Does NOT cover:** Web/mobile apps, cloud infrastructure, enterprise software, data science

---

## Cross-Role Coverage Matrix

| Concern | Primary Role | Supporting Roles |
|---------|-------------|-----------------|
| API design | Backend | System Architect, Security |
| Database schema | Backend + DBA | Data Engineer |
| UI/UX implementation | Frontend | Research Engineer |
| Mobile apps | iOS / Android | Backend, Security |
| Data pipelines | Data Engineer | DBA, Data Scientist |
| ML in production | AI/ML Engineer | Data Scientist, Backend |
| Cloud infrastructure | Infrastructure Engineer | Security, System Architect |
| App security | Security Engineer | ALL roles |
| Performance | Production Engineer | Backend, Frontend, DBA |
| Code quality | Code Health Engineer | ALL roles |
| Spec compliance | Requirements Engineer | ALL roles |
| Technology decisions | Research Engineer | System Architect |
| System design | System Architect | Backend, Infrastructure |
| Bug verification | Production Engineer | Code Health, QA concerns |
| Game systems | Game Developer | Backend (multiplayer) |
| Hardware/firmware | Embedded/IoT | Security, Backend (cloud) |
