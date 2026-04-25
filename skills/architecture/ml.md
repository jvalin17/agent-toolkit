# ML/AI Architecture

Decisions for the ML/AI layer of the system. Only relevant when requirements include ML/AI capabilities.

## Inputs

Read `requirements/<name>.md` and extract:
- **ML/AI Requirements** section — what ML/AI capabilities are needed, what problems they solve
- **Algorithm / Model Preference** section — if the user specified an algorithm or architecture, use it as a constraint. Validate that infrastructure decisions support it. If marked "out of scope," acknowledge it and focus on what CAN be built (data pipeline, API layer, integration scaffolding)
- **Data sources** — what data is available, format, volume, update frequency
- **Non-functional requirements** — latency targets, cost constraints, privacy requirements
- **Regulatory/compliance** — industry regulations affecting model decisions

Also read the Quick Architecture from `architecture/<name>.md` for the chosen architecture pattern and tech stack.

---

### Decision 1: Model Serving Approach

**Context:** How the application runs ML models at inference time. The foundational ML architecture decision.

**Options:**

| | Option A: API-Based (OpenAI, Claude, HuggingFace Inference) | Option B: Self-Hosted (vLLM, TGI, TorchServe) | Option C: Edge/On-Device (ONNX, TFLite, Core ML) | Option D (local/cheap): API with Free Tiers or Ollama |
|---|---------|---------|---------|---------|
| What | Call an external API for inference | Run models on your own infrastructure | Run models directly on user devices | Free API tiers or local inference with Ollama |
| Best for | Quick start, no ML infra expertise, general-purpose models | Data privacy, custom models, high throughput, cost control at scale | Offline use, mobile apps, latency-critical applications | Prototypes, development, cost-sensitive projects |
| Trade-off | Data leaves your network, per-request cost, vendor lock-in | Infrastructure complexity, GPU costs, model management | Limited model size, device-specific optimization, update complexity | Rate limits, smaller models (Ollama), limited throughput |
| Cost | Per-token/request pricing ($0.01-$0.10+ per request) | GPU server costs ($50-500+/mo), but predictable | Development cost for optimization, no inference cost | Free or near-free |
| SOLID/DRY check | ✅ Simple integration | ✅ Full control | ⚠️ Platform-specific code needed | ✅ Simplest path to working system |

**Decision tree:** "If data can leave your network → API is simplest. If privacy/latency/cost matters at scale → self-hosted. If offline capability is needed → edge."

**If user specified a custom algorithm:** Does this serving approach support running it? A CNN needs GPU serving, not a CPU-only API. An RL agent needs environment simulation. Validate the match.

Launch `tech-stack-advisor` if the user is unsure.

**Consequence:** Shapes pipeline architecture, cost model, and data flow. If API-based, skip Decision 2 (no training pipeline needed).

---

### Decision 2: ML Pipeline Architecture

**Context:** Where training happens and how models are versioned and deployed. Skip if using API-based serving only (Decision 1, Option A). Depends on model serving approach.

**Options:**

| | Option A: Notebook-Based (Jupyter) | Option B: Pipeline Framework (Kubeflow, Airflow, Metaflow) | Option C: Managed Service (SageMaker, Vertex AI) | Option D (local/cheap): Jupyter + MLflow |
|---|---------|---------|---------|---------|
| What | Train in notebooks, export model, deploy manually | DAG-based workflows for data prep, training, evaluation, deployment | Cloud-managed end-to-end ML platform | Notebooks for training, MLflow for experiment tracking |
| Best for | Research, prototyping, solo data scientists | Production ML with reproducibility requirements | Teams without ML infrastructure expertise | Small teams, early-stage ML products |
| Trade-off | Not reproducible, hard to automate, no versioning | Complex setup, operational overhead | Vendor lock-in, cost at scale | Manual deployment, limited automation |
| Cost | Free (Jupyter) | Free (open source) + infrastructure | Pay-per-use ($10-1000+/mo) | Free (both open source) |
| SOLID/DRY check | ⚠️ No separation of concerns | ✅ Each step is a clear module | ✅ Managed boundaries | ✅ Simple with tracking |

**If user specified a custom algorithm:** Ensure the pipeline supports training it. Examples:
- Reinforcement learning needs environment simulation in the pipeline
- GANs need generator + discriminator training loops
- Large language model fine-tuning needs large GPU memory and gradient checkpointing

**Consequence:** Affects how models are versioned, how retraining is triggered, and how deployments happen.

---

### Decision 3: Feature Engineering & Data Pipeline

**Context:** How data gets from raw sources to model-ready format. Depends on model serving (Decision 1) and pipeline (Decision 2).

**Options:**

| | Option A: Batch Processing | Option B: Streaming (Real-Time Features) | Option C: On-Demand (Compute at Inference Time) |
|---|---------|---------|---------|
| What | Scheduled transforms (hourly/daily) that precompute features | Real-time feature computation from event streams | Features computed when a prediction is requested |
| Best for | Offline models, batch predictions, historical features | Real-time recommendations, fraud detection | Simple features, low-volume inference |
| Trade-off | Stale features (lag between event and feature update) | Complex infrastructure (Kafka, Flink), harder to debug | Higher inference latency, recomputation cost |
| Cost | Low (scheduled compute) | High (always-on stream processing) | Low (per-request compute) |
| SOLID/DRY check | ✅ Clear batch boundaries | ⚠️ Complex, but well-separated if designed right | ✅ Simple, self-contained |

**Storage options:**

| | Feature Store (Feast, Tecton) | Database Views | Precomputed Tables |
|---|---------|---------|---------|
| What | Dedicated feature storage with point-in-time correctness | SQL views that compute features on query | Materialized tables refreshed on schedule |
| Best for | Multiple models sharing features, time-travel queries | Simple features, SQL-native teams | Medium complexity, good performance |
| Trade-off | New infrastructure to manage | Query performance at scale | Staleness, storage cost |

**Local/cheap alternative:** pandas transforms + SQLite/DuckDB for batch processing.

**Consequence:** Affects model accuracy (feature freshness), inference latency, and infrastructure complexity.

---

### Decision 4: Model Evaluation & Monitoring

**Context:** How to know if the model is working and when it degrades. Depends on serving approach (Decision 1).

**Options:**

| | Option A: Offline Evaluation Only | Option B: Offline + Online Monitoring | Option C: Full MLOps (Offline + Online + Automated Retraining) |
|---|---------|---------|---------|
| What | Test sets, cross-validation, manual evaluation before deploy | Add production monitoring for accuracy drift, data drift, latency | Automated detection of degradation with triggered retraining |
| Best for | Early-stage, low-risk applications | Production ML systems | High-stakes, high-volume ML systems |
| Trade-off | No visibility into production performance | Monitoring infrastructure needed | Complex automation, risk of training on bad data |
| Cost | Free (part of training) | Monitoring tools ($0-100/mo) | Significant engineering investment |
| SOLID/DRY check | ✅ Simple | ✅ Clear separation of offline/online | ⚠️ Complex automation must be well-separated |

**Key monitoring dimensions:**
- **Accuracy drift:** Model performance declining over time (ground truth comparison)
- **Data drift:** Input distribution changing from training data (statistical tests)
- **Latency tracking:** Inference time increasing (p50, p95, p99)
- **Alerting triggers:** What triggers retraining or rollback? Define thresholds.

**Consequence:** Affects operational load, alerting strategy, and retraining pipeline design.

---

### Decision 5: Cost Management

**Context:** Especially critical for API-based models (Decision 1, Option A). Controls budget and prevents surprise bills.

**Options:**

| | Option A: Token/Request Budgets | Option B: Smart Routing (Model Cascade) | Option C: Aggressive Caching |
|---|---------|---------|---------|
| What | Hard limits per user/feature on API usage | Expensive model for hard cases, cheap model for easy ones | Cache responses to avoid redundant API calls |
| Best for | Predictable costs, SaaS with user tiers | Optimizing cost/quality trade-off | Repetitive queries, similar inputs |
| Trade-off | Users hit limits, degraded experience | Complexity in routing logic, latency for routing decision | Stale responses, cache size management |
| Cost | Saves money via hard caps | 40-80% cost reduction typical | Storage cost for cache, but major API cost savings |
| SOLID/DRY check | ✅ Clear budget boundaries | ✅ Strategy pattern — clean separation | ✅ Transparent caching layer |

**Caching strategies:**
- **Exact-match cache:** Same prompt → same response (simple, high hit rate for repetitive tasks)
- **Semantic cache:** Similar prompts → cached response (embedding-based similarity, complex but broader coverage)
- **Prompt caching:** Provider-level caching (Anthropic prompt caching, reduces cost for shared prefixes)

**Rate limiting:** Per user, per feature, per time window. Align with API rate limiting decisions from backend architecture.

**Consequence:** Affects user experience (degradation when limits hit), infrastructure (cache layer), and business model.

---

### Decision 6: Responsible AI

**Context:** Only go deep if requirements mention explainability, auditability, or the project is in a regulated industry (healthcare, finance, legal, hiring). Otherwise, note basic best practices and move on.

**Options:**

| | Option A: Basic Best Practices | Option B: Explainability Layer | Option C: Full Governance Framework |
|---|---------|---------|---------|
| What | Document model limitations, basic bias checks, human review for critical decisions | Add explainability tools (SHAP, LIME, attention weights, chain-of-thought) | Audit trail, bias detection, fairness metrics, human-in-the-loop, model cards |
| Best for | Low-risk applications (content generation, search) | Medium-risk (recommendations, scoring) | High-risk (healthcare, finance, legal, hiring) |
| Trade-off | Minimal effort, some risk | Added infrastructure and latency for explanations | Significant engineering and process overhead |
| Cost | Free (documentation) | Moderate (tooling) | High (tooling + process + compliance) |
| SOLID/DRY check | ✅ Minimal overhead | ✅ Separate explainability module | ✅ Governance as a cross-cutting concern |

**Key components (choose based on risk level):**
- **Explainability:** SHAP values, LIME, attention visualization, chain-of-thought reasoning
- **Bias detection:** Statistical parity, equalized odds, demographic parity testing
- **Audit trail:** Log every model decision with inputs, outputs, model version, and confidence
- **Human-in-the-loop:** Define which decisions require human review before acting
- **Model cards:** Document model purpose, limitations, evaluation metrics, and intended use

**Consequence:** Affects logging infrastructure, model serving latency, and compliance posture.

---

## Decision Format Reference

Each decision above follows the standard format from the base SKILL.md. For guardrails (G-ARCH-1 through G-ARCH-4, G1-G9), see `shared/guardrails.md` — they are not duplicated here.
