# Role Responsibilities by Scenario

> Derived from 62 open-source repos across all categories
> Date: 2026-08-16
> Status: FINAL — locked with 19 roles

## Scenarios Extracted (from 62 repos)

| # | Scenario | Example Repos |
|---|----------|---------------|
| S1 | Build a SaaS app (auth, billing, dashboard) | Twenty, Cal.com, PostHog, Plane |
| S2 | Build an e-commerce platform | Medusa, Saleor |
| S3 | Build a real-time collaboration app | AppFlowy, Mattermost, Plane |
| S4 | Build an encrypted/security-first app | Signal, Vaultwarden, Infisical |
| S5 | Build an API platform / developer tool | Hoppscotch, Firecrawl, LiteLLM, Strapi |
| S6 | Build a mobile app (iOS) | Signal iOS, Wikipedia iOS, Firefox iOS |
| S7 | Build a mobile app (Android) | Signal Android, Wikipedia Android, Firefox Android |
| S8 | Build a cross-platform app | AppFlowy (Flutter+Rust), Expensify (RN), Mattermost Mobile |
| S9 | Build an AI/ML application | Dify, Open WebUI, Mem0, Ollama |
| S10 | Build a data/analytics platform | PostHog, SigNoz, Plausible, Dagster |
| S11 | Build an IoT/embedded system | Home Assistant, ESPHome, ThingsBoard |
| S12 | Build a game | Godot Engine |
| S13 | Build a desktop app | GitButler (Tauri), Firefox, AppFlowy |
| S14 | Build a CLI tool | Bun, Ollama |
| S15 | Build infrastructure/DevOps tooling | Crossplane, Gitea, Supabase |
| S16 | Modernize a legacy system | OpenEMR (20yr PHP), Firefox iOS (Cordova→native) |
| S17 | Migrate database (e.g., PostgreSQL→ClickHouse) | PostHog |
| S18 | Build a CMS/content platform | Payload, Strapi |
| S19 | Handle healthcare/regulated compliance | OpenEMR, Metriport |
| S20 | Build at mega-scale (millions of users) | Linux, Kubernetes, Chromium |
| S21 | Build a payment system | Hyperswitch (50+ processors) |
| S22 | Build an observability/monitoring system | SigNoz, PostHog |
| S23 | Build a multi-tenant platform | Twenty, ThingsBoard, Cal.com |
| S24 | Language migration (Java→Kotlin, C→Rust) | Signal Android, Linux Kernel |
| S25 | Build a plugin/extension system | Godot, Strapi, Medusa, Home Assistant |
| S26 | Build offline-first with sync | AppFlowy, Wikipedia iOS/Android, Expensify, Signal |
| S27 | Build a document processing system | Documenso, Stirling-PDF |
| S28 | Manage a monorepo at scale | Cal.com (Turborepo), Firefox Android |
| S29 | Build regression test suite for existing app | All repos with documented testing |
| S30 | Convert/wrap web app for mobile (Capacitor/etc.) | Cross-platform approaches |

---

## Responsibilities by Role × Scenario

### 1. Backend Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Design REST/GraphQL API, auth system (OAuth, JWT), session management, webhook handlers, Stripe integration, background jobs for emails/notifications |
| S2 E-commerce | Product catalog API, cart/checkout flow, inventory management, order processing, tax calculation, multi-currency, payment gateway abstraction |
| S3 Real-time | WebSocket server, message routing, presence tracking, typing indicators, connection management, message persistence |
| S4 Security-first | Encrypted API endpoints, key exchange protocols, sealed sender implementation, zero-knowledge architecture |
| S5 API platform | API design (OpenAPI spec), rate limiting (token bucket), API key management, versioning strategy, SDK-friendly response formats |
| S9 AI/ML app | LLM API proxy, streaming response handling, embedding pipeline endpoints, RAG retrieval API, token usage tracking |
| S10 Analytics | Event ingestion API (high-throughput), query API for dashboards, data export endpoints, webhook delivery system |
| S21 Payments | Payment routing logic, idempotent transaction handling, 3DS orchestration, refund/chargeback flows, multi-processor failover |
| S23 Multi-tenant | Tenant isolation (schema per tenant vs row-level), tenant-aware middleware, resource limits per tenant |
| S25 Plugin system | Plugin API design, hook/event system, plugin sandboxing, registry management |
| S26 Offline-first | Sync protocol design, conflict resolution endpoints, delta sync API, last-write-wins vs merge strategies |

---

### 2. Frontend Developer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Dashboard UI, data tables with pagination/filtering/sorting, charts/visualizations, form builders, settings pages, responsive layout |
| S2 E-commerce | Product listing, search/filter, cart UI, checkout flow, payment form (Stripe Elements), order tracking |
| S3 Real-time | Chat UI, message threading, typing indicators, presence dots, real-time list updates, notification badges |
| S5 API platform | Interactive API explorer, request builder UI, response viewer with syntax highlighting, environment variable management |
| S10 Analytics | Dashboard builder, chart components (line, bar, funnel, retention), date range pickers, query builder UI, data table with export |
| S13 Desktop | Tauri/Electron shell, native menu integration, file system access, system tray, keyboard shortcuts, window management |
| S18 CMS | WYSIWYG editor, content modeling UI, media library, drag-drop field builder, live preview, localization UI |
| S27 Document | PDF viewer/editor, field placement UI, signature capture, document upload with preview, multi-page navigation |
| S30 Web→Mobile | Capacitor/Ionic wrapper setup, responsive→adaptive conversion, touch gesture adaptation, native plugin bridges |

---

### 3. iOS Developer

| Scenario | Responsibilities |
|----------|-----------------|
| S6 iOS app | SwiftUI/UIKit views, navigation (NavigationStack), Core Data/SwiftData persistence, Keychain storage, push notifications (APNs), background fetch |
| S4 Security-first | Keychain Services for keys, certificate pinning, biometric auth (Face/Touch ID), App Transport Security, encrypted SQLite (SQLCipher) |
| S8 Cross-platform | Swift Package Manager modules for shared logic, platform-specific UI (iOS vs iPadOS), App Clips, widgets (WidgetKit) |
| S26 Offline-first | Core Data with CloudKit sync, offline article/content caching, background sync with BGTaskScheduler, conflict resolution UI |
| S30 Web→Mobile | Evaluate Capacitor vs native, native module bridges for camera/push/payments, App Store submission, TestFlight beta |
| S6 (Wikipedia) | Hybrid WebView + native chrome, 300+ language support, Dynamic Type, VoiceOver accessibility, reading lists with offline support |
| S6 (Signal) | Rust FFI bridge (libsignal), encrypted database migrations, notification service extension for decryption, device linking protocol |
| S6 (Firefox) | Redux-inspired state management, Swift Package Manager modular architecture, SwiftUI migration from UIKit, WebKit rendering |

---

### 4. Android Developer

| Scenario | Responsibilities |
|----------|-----------------|
| S7 Android app | Jetpack Compose UI, ViewModel + LiveData/Flow, Room database, WorkManager for background tasks, FCM push notifications, deep links |
| S4 Security-first | Encrypted SharedPreferences, SQLCipher database, JNI bridge to Rust (libsignal), certificate pinning, biometric prompt |
| S8 Cross-platform | Gradle multi-module structure, shared Kotlin Multiplatform logic, platform-specific UI, Play Store + sideload APK distribution |
| S26 Offline-first | Room with sync adapter, WatermelonDB for React Native, offline content caching, WorkManager for deferred sync |
| S7 (Signal) | FCM with WebSocket fallback (degoogled devices), custom camera/media picker, Java→Kotlin migration, JNI to Rust |
| S7 (Firefox) | GeckoView integration (own rendering engine), monorepo (Fenix + Focus + Components), WebExtension add-on support on mobile |
| S7 (Wikipedia) | Multi-module Gradle, content editing (wikitext editor), 300+ language RTL/CJK support, TalkBack accessibility |

---

### 5. DBA

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Schema design for users/orgs/subscriptions, index strategy for common queries, connection pooling config |
| S2 E-commerce | Product/order/inventory schema, index for product search, transaction isolation for inventory reservation |
| S3 Real-time | Message storage schema (partitioned by channel/time), index for message retrieval, archive strategy for old messages |
| S10 Analytics | ClickHouse table design for event storage, materialized views for dashboards, retention policies, partition management |
| S17 DB migration | Migration plan (PostgreSQL→ClickHouse), data transfer pipeline, dual-write period, query translation, rollback plan |
| S20 Mega-scale | Replication topology, sharding strategy, read replicas, connection limit management, vacuum tuning, pg_stat_statements analysis |
| S21 Payments | Transaction table design with audit trail, ACID guarantees for financial data, encrypted columns for PII, point-in-time recovery |
| S23 Multi-tenant | Schema-per-tenant vs shared schema with row-level security, tenant isolation verification, per-tenant backup capability |

---

### 6. Data Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S10 Analytics | Event ingestion pipeline (Kafka→ClickHouse), ETL for dashboard aggregations, data quality checks, schema registry |
| S9 AI/ML app | Feature pipeline for model training, embedding generation pipeline, vector store ingestion, data versioning |
| S17 DB migration | CDC pipeline from old DB to new, data validation during migration, backfill scripts, data lineage tracking |
| S19 Regulated | HIPAA-compliant data pipelines, audit logging pipeline, data anonymization/pseudonymization, data retention automation |
| S22 Observability | Log aggregation pipeline, metrics ingestion, trace collection, data routing to multiple backends |
| S27 Document | Document processing pipeline (PDF→text→embeddings), OCR pipeline, batch processing for bulk documents |

---

### 7. Data Scientist

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Churn prediction model prototype, user segmentation, funnel analysis, A/B test design for pricing/features |
| S2 E-commerce | Recommendation engine prototype, conversion funnel analysis, pricing optimization experiments |
| S9 AI/ML app | Model evaluation metrics, experiment tracking setup, bias/fairness analysis, benchmark dataset curation |
| S10 Analytics | Statistical engine for A/B testing (power analysis, sequential testing), metric definition, anomaly detection |
| S20 Mega-scale | Capacity forecasting models, user growth modeling, engagement metric design |

---

### 8. AI/ML Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S9 AI/ML app | RAG pipeline (chunking, embedding, retrieval, generation), LLM integration (API wrappers, prompt chains), vector DB setup (pgvector/Qdrant/Pinecone), model serving infrastructure, fine-tuning pipeline, guardrails |
| S1 SaaS | AI feature integration (AI-powered search, auto-categorization), embedding-based similarity, LLM-powered summarization |
| S2 E-commerce | Product recommendation serving, search ranking model, image similarity search |
| S3 Real-time | AI-powered message suggestions, smart notifications, content moderation ML pipeline |
| S10 Analytics | Anomaly detection model serving, time-series forecasting, automated insight generation |
| S11 IoT | Edge ML inference on microcontrollers, model quantization for embedded, sensor data classification |

---

### 9. Infrastructure Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Cloud infrastructure (VPC, subnets, LB), CI/CD pipeline, container orchestration, auto-scaling, monitoring/alerting stack |
| S10 Analytics | ClickHouse cluster management, Kafka cluster ops, high-throughput ingestion infrastructure, storage optimization |
| S11 IoT | MQTT broker deployment, device provisioning infrastructure, OTA update delivery, edge computing setup |
| S15 Infra tooling | Kubernetes operator development, CRD design, reconciliation loops, Terraform modules |
| S19 Regulated | HIPAA-compliant infrastructure, audit logging infrastructure, encryption at rest/transit, access control |
| S20 Mega-scale | Multi-region deployment, CDN configuration, disaster recovery, capacity planning, cost optimization |
| S22 Observability | Prometheus/Grafana stack, log aggregation (Loki/ELK), distributed tracing (Jaeger/Tempo), alert routing |
| S23 Multi-tenant | Tenant-isolated infrastructure, resource quotas per tenant, noisy-neighbor prevention |
| S28 Monorepo | CI/CD for monorepo (Turborepo remote caching, affected-package detection, parallel builds) |

---

### 10. Security Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Auth architecture review, CSRF/XSS prevention, session management audit, dependency vulnerability scan |
| S4 Security-first | Cryptographic protocol review, key management audit, zero-knowledge architecture validation, penetration testing |
| S5 API platform | API key security, rate limiting review, injection prevention, OAuth flow validation |
| S11 IoT | Firmware signing verification, device identity management, secure boot chain review, communication encryption audit |
| S19 Regulated | HIPAA security rule compliance, SOC 2 controls implementation, access control audit, encryption verification |
| S21 Payments | PCI-DSS compliance, payment data handling review, tokenization verification, fraud detection integration |
| S24 Migration | Security regression check during migration, dependency audit of new stack, secret rotation during transition |
| ALL scenarios | Dependency vulnerability scanning, license compliance checking, SBOM generation, supply chain risk assessment |

---

### 11. Production Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Run app locally, click through all flows (signup→dashboard→settings), verify Stripe webhooks process, check email delivery |
| S2 E-commerce | Test full purchase flow (browse→cart→checkout→payment→confirmation), verify inventory updates, test refund flow |
| S3 Real-time | Verify messages deliver in real-time, test reconnection on network drop, check typing indicators, load test concurrent users |
| S6/S7 Mobile | Install on device/simulator, test all screens, verify push notifications, check offline→online transition, test deep links |
| S9 AI/ML | Test LLM responses with various inputs, verify RAG retrieval accuracy, check streaming token delivery, measure response latency |
| S16 Modernize | Run old and new system side-by-side, compare outputs for equivalence, verify no regression in user-facing behavior |
| S17 DB migration | Verify data integrity after migration, compare query results old vs new, check no data loss, measure new query performance |
| S21 Payments | Test payment flows in sandbox, verify webhook delivery, check refund processing, test failure scenarios (declined cards) |
| ALL scenarios | Measure response times, identify slowness, check error rates, verify deployment success, test edge cases in real environments |

---

### 12. QA Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Design test strategy (unit/integration/E2E ratio), create test environments (staging, preview), write E2E tests for critical flows, regression suite for auth/billing |
| S2 E-commerce | Cart edge cases (empty cart, max quantity, out-of-stock during checkout), payment failure scenarios, multi-currency test data |
| S3 Real-time | Concurrency tests (multiple users editing same document), message ordering tests, reconnection scenarios, offline queue tests |
| S6/S7 Mobile | Device matrix testing (screen sizes, OS versions), app lifecycle tests (background/foreground), network condition simulation (2G, airplane mode) |
| S8 Cross-platform | Feature parity tests across platforms, platform-specific behavior verification, shared test suite for business logic |
| S16 Modernize | Build regression test suite BEFORE migration, characterization tests for legacy behavior, golden master testing |
| S20 Mega-scale | Load testing (identify saturation point, not just "can handle N users"), chaos engineering, failure injection |
| S29 Regression suite | Risk-based test prioritization, mutation testing for test quality, contract testing for microservices, test data management |
| ALL scenarios | Exploratory testing, edge case discovery (SFDIPOT heuristic), flaky test detection and fixing, test environment provisioning |

---

### 13. System Architect

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Monolith vs microservices decision, data model design, caching strategy, API contract design, tech stack selection with ADRs |
| S3 Real-time | CRDT vs OT decision for collaboration, event bus architecture, WebSocket vs SSE vs polling decision, consistency model |
| S8 Cross-platform | Shared core architecture (Flutter+Rust FFI, React Native+native modules), code sharing strategy, platform abstraction layer |
| S10 Analytics | Event pipeline architecture (Kafka→ClickHouse), query engine design, storage tiering (hot/warm/cold), retention strategy |
| S15 Infra tooling | Kubernetes operator pattern, CRD schema design, reconciliation loop architecture, plugin API design |
| S16 Modernize | Strangler fig vs rewrite decision, migration phases, parallel run architecture, feature flag strategy for gradual rollout |
| S20 Mega-scale | Multi-region architecture, data partitioning strategy, consistency vs availability tradeoffs (CAP), capacity planning (Little's Law) |
| S21 Payments | Payment orchestration architecture, processor failover design, idempotency strategy, audit trail design |
| S23 Multi-tenant | Isolation model (shared vs dedicated resources), tenant routing, resource limit architecture, data segregation |
| S25 Plugin system | Extension point design, plugin lifecycle management, sandboxing architecture, API stability guarantees |
| ALL scenarios | ADR documentation, build vs buy evaluation, technology selection with tradeoffs, non-functional requirement specification |

---

### 14. Code Health Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S16 Modernize | Codebase assessment (complexity hotspots, dependency graph, dead code), tech debt inventory, safe refactoring plan |
| S20 Mega-scale | Backward compatibility enforcement ("don't break userspace"), API deprecation management, dependency upgrade strategy |
| S24 Migration | Language migration safety (Java→Kotlin, C→Rust), verify behavioral equivalence, incremental migration tracking |
| S28 Monorepo | Dependency graph health, circular dependency detection, package boundary enforcement, build time monitoring |
| S29 Regression suite | Test suite health audit, flaky test identification, coverage gap analysis, mutation testing setup |
| ALL scenarios | Blast radius analysis before changes, dependency health monitoring (abandoned packages, CVEs), code complexity tracking, refactoring safety verification (behavior snapshot before/after) |

---

### 15. Requirements Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Feature spec→code mapping (every user story has implementation + test), acceptance criteria verification |
| S2 E-commerce | Product catalog requirements tracking, checkout flow completeness (all payment methods, edge cases), localization requirements |
| S8 Cross-platform | Feature parity tracking across platforms (iOS has X, Android missing Y), platform-specific requirement documentation |
| S16 Modernize | Reverse-engineer existing system requirements, document current behavior as spec, gap detection during migration |
| S19 Regulated | Compliance requirement tracking (HIPAA checklist items→code), audit evidence mapping, regulation change propagation |
| S24 Migration | Feature completeness verification (old system vs new), API contract preservation, behavioral equivalence tracking |
| ALL scenarios | Scope drift detection, requirement change impact analysis, requirement-to-test mapping, acceptance criteria clarity |

---

### 16. Research Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Best auth provider (Clerk vs Auth.js vs Lucia), best ORM (Prisma vs Drizzle vs Kysely), best UI library (shadcn vs Radix vs Mantine) |
| S2 E-commerce | Headless commerce options (Medusa vs Saleor vs custom), payment processor comparison, search solution (Algolia vs Meilisearch vs Typesense) |
| S3 Real-time | CRDT libraries (Yjs vs Automerge), WebSocket libraries, collaboration framework options |
| S8 Cross-platform | Flutter vs React Native vs Capacitor analysis (with evidence from AppFlowy, Expensify, Mattermost), Tauri vs Electron for desktop |
| S9 AI/ML | Vector DB comparison (pgvector vs Pinecone vs Qdrant vs Weaviate), RAG framework options (LangChain vs LlamaIndex), LLM provider evaluation |
| S10 Analytics | ClickHouse vs TimescaleDB vs QuestDB for time-series, event tracking approaches, dashboard framework options |
| S11 IoT | Communication protocol selection (MQTT vs CoAP vs BLE — range/power/bandwidth tradeoffs), RTOS options, OTA update frameworks |
| S13 Desktop | Tauri vs Electron (from GitButler, AppFlowy evidence), native vs cross-platform for desktop |
| S16 Modernize | Modern equivalents for legacy components, migration strategy research (strangler fig examples), framework upgrade guides |
| S21 Payments | Payment processor landscape, PCI-DSS compliance approaches, fraud detection options |
| CONTINUOUS | Academic papers (arxiv CS/SE/ML), company engineering blogs (Netflix, Uber, Stripe, Meta, Vercel, Cloudflare), framework changelogs, Hacker News trends, conference talk summaries |

---

### 17. Game Developer

| Scenario | Responsibilities |
|----------|-----------------|
| S12 Game | Game loop implementation (fixed timestep), ECS architecture, physics integration (collision detection, raycasting), rendering pipeline (shaders, draw call batching), animation system, audio system (spatial audio, mixing), input handling (keyboard/mouse/gamepad/touch) |
| S12 (Godot) | Custom scripting language runtime (GDScript), Vulkan rendering pipeline, GDExtension FFI for native plugins, scene tree architecture, cross-platform export (PC/mobile/web), editor-as-application |
| S12 Multiplayer | Client-side prediction, server reconciliation, lag compensation, state synchronization, lobby/matchmaking system |
| S12 Performance | Frame rate targeting (30/60/120 FPS), GC pressure reduction, object pooling, memory allocation optimization, draw call batching |

---

### 18. Embedded/IoT Developer

| Scenario | Responsibilities |
|----------|-----------------|
| S11 IoT | Firmware for microcontrollers, sensor data acquisition (I2C/SPI/UART drivers), RTOS task scheduling, MQTT/CoAP communication, OTA update system, power management (sleep modes, duty cycling) |
| S11 (Home Assistant) | Integration protocol implementation (2800+ integrations), event-driven automation engine, device state management, YAML configuration parsing |
| S11 (ESPHome) | Configuration-based firmware generation, sensor driver library, WiFi/BLE connectivity, MQTT publishing, OTA via WiFi |
| S11 (ThingsBoard) | Multi-protocol ingestion (MQTT, CoAP, HTTP, LwM2M, Modbus, OPC-UA), device provisioning, rule engine for event processing, time-series data optimization |
| S11 Performance | Power consumption optimization per operation, memory usage within constraints (64-256KB RAM), real-time guarantee verification, interrupt handling |

---

### 19. Legal & Compliance Engineer

| Scenario | Responsibilities |
|----------|-----------------|
| S1 SaaS | Privacy policy generation based on data collected, cookie consent (GDPR/ePrivacy), Terms of Service, data processing agreements |
| S2 E-commerce | Consumer protection laws per market, return/refund legal requirements, tax compliance (VAT, sales tax by jurisdiction), cross-border selling regulations |
| S6/S7 Mobile | App Store privacy labels (Apple), Data Safety Section (Google Play), age rating compliance, data collection disclosures |
| S9 AI/ML | EU AI Act compliance, algorithmic transparency requirements, AI-generated content disclosure, data usage for training consent |
| S11 IoT | Data collection disclosure for devices, GDPR for smart home data, children's privacy (COPPA if applicable), device data retention policies |
| S19 Regulated | HIPAA compliance (health), FERPA (education), PCI-DSS (payments), SOX (finance), FedRAMP (government), country-specific health data laws |
| S21 Payments | PCI-DSS scope assessment, money transmitter licensing by jurisdiction, PSD2 compliance (EU), payment data retention limits |
| S24 Migration | License compatibility analysis (GPL→MIT implications), open-source obligation tracking, contributor license agreements |
| WORLDWIDE | Per-country privacy laws (GDPR, CCPA, LGPD, PIPEDA, PDPA, POPI), data residency requirements, accessibility legal mandates (ADA, EAA), export controls (encryption — EAR/ITAR), content moderation laws (DSA, Section 230) |
| ALL scenarios | Open-source license compliance scanning, dependency license compatibility, SBOM for legal audit, trademark/IP considerations |

---

## Scenario Coverage Matrix

Which roles are active per scenario type:

```
Scenario          BE FE iOS And DBA DE DS ML  Inf Sec Prod QA  Arc CH  Req Res Game Emb Legal
S1  SaaS          x  x              x                x   x   x   x   x   x   x   x              x
S2  E-commerce    x  x              x                x   x   x   x   x   x   x   x              x
S3  Real-time     x  x              x            x   x   x   x   x   x   x   x   x
S4  Security      x              x                   x   x   x       x       x
S5  API platform  x  x                               x   x   x   x   x   x   x   x
S6  iOS           x      x                          x   x   x       x   x   x               x
S7  Android       x          x                       x   x   x       x   x   x               x
S8  Cross-plat    x  x   x   x                      x   x   x   x   x   x   x   x           x
S9  AI/ML         x              x   x   x   x   x  x   x   x       x       x              x
S10 Analytics     x  x          x   x   x   x   x   x   x   x   x   x   x   x   x
S11 IoT           x                          x   x       x   x       x       x        x     x
S12 Game                                                  x   x   x           x   x
S13 Desktop       x  x                                    x   x       x   x   x   x
S14 CLI           x                                       x   x           x   x
S15 Infra tool    x                              x   x   x   x       x       x
S16 Modernize     x  x                          x   x   x   x   x   x   x   x   x
S17 DB migration  x          x   x               x       x   x   x   x   x
S18 CMS           x  x          x                    x   x   x       x       x
S19 Regulated     x              x   x               x   x   x       x   x   x              x
S20 Mega-scale    x          x   x               x   x   x   x   x   x       x
S21 Payments      x          x                   x   x   x   x   x   x   x   x              x
S22 Observability x                  x           x       x   x       x       x
S23 Multi-tenant  x          x                   x   x   x   x   x   x   x
S24 Migration     x                              x   x   x   x   x   x   x   x              x
S25 Plugin        x  x                               x   x   x   x   x       x
S26 Offline-first x  x   x   x                       x   x   x       x       x
S27 Document      x  x          x   x                    x   x       x       x
S28 Monorepo                                     x       x       x   x
S29 Regression                                        x   x       x   x
S30 Web→Mobile    x  x   x   x                       x   x   x       x   x   x
```

## Role Activity Summary

| Role | Active in N/30 scenarios | Most active in |
|------|--------------------------|----------------|
| Backend Engineer | 27/30 | Nearly everything |
| Security Engineer | 26/30 | Cross-cutting |
| Production Engineer | 25/30 | Cross-cutting |
| Research Engineer | 24/30 | Cross-cutting |
| QA Engineer | 22/30 | Cross-cutting |
| Frontend Developer | 20/30 | Web/SaaS/desktop |
| System Architect | 20/30 | Design-heavy scenarios |
| Code Health Engineer | 18/30 | Maintenance/migration |
| Requirements Engineer | 18/30 | Compliance/migration |
| DBA | 15/30 | Data-heavy scenarios |
| Infrastructure Engineer | 15/30 | Scale/deployment |
| Legal & Compliance | 12/30 | Regulated/public-facing |
| iOS Developer | 8/30 | Mobile scenarios |
| Android Developer | 8/30 | Mobile scenarios |
| Data Engineer | 8/30 | Data/analytics |
| AI/ML Engineer | 6/30 | AI-specific |
| Data Scientist | 5/30 | Analytics/experiments |
| Game Developer | 3/30 | Game-specific |
| Embedded/IoT | 3/30 | IoT-specific |

## Next Steps

1. Roles + responsibilities are defined
2. Update architecture doc (v4) with final 19 roles
3. Begin knowledge acquisition:
   - Curate repos.json per role
   - Build indexer pipeline
   - Start with top 6 most active roles: Backend, Security, Production, Research, QA, Frontend
