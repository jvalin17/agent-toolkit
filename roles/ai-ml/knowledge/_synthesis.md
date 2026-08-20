---
role: ai-ml
sources: 7
synthesized_at: 2026-08-17T01:54:23.330565
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
This role covers LLM serving/gateways, RAG pipelines, embeddings, vector DB abstraction, memory systems, model format conversion, and MLOps concerns (caching, cost tracking, observability). Sources: litellm (LLM gateway), dify (LLM app platform), mem0 (memory layer), ollama (local inference server), open-webui (LLM frontend/RAG), plus two thin web sources (Spotify blog — 404'd, content not captured; Anthropic prompt-engineering docs — workflow guidance only).

## Patterns Found (ranked by frequency)

**1. Provider/Plugin Abstraction with Factory (5/5 repos)** — Every repo abstracts LLM/embedding/vector-DB providers behind a base interface + factory:
- litellm: `litellm/llms/<provider>/` each with `main.py` + `transformation.py`, normalized to `ModelResponse`
- mem0: `mem0/utils/factory.py` — `EmbedderFactory.create("openai", config)` → class instantiation; `base.py` per component dir
- dify: `api/providers/vdb/` (one subdir per vector DB), `api/factories/agent_factory.py`
- ollama: `convert/convert_<arch>.go` converters sharing common interface; per-model `parsers/` + `renderers/`
- open-webui: provider routing in `backend/open_webui/routers/`, OpenAI format as canonical interface

**2. Pluggable Vector DB Layer (4/5)** — dify (11 backends incl. pgvector, Milvus, Qdrant, Weaviate), mem0 (20+, Qdrant default hard dep), open-webui (8, ChromaDB default), litellm (Qdrant/Redis for semantic cache). All select via config, not code.

**3. Pydantic Config Objects (3/5)** — mem0 (`{Component}Config` paired classes, `Memory.from_config(dict)`), litellm (`pydantic-settings` from env), dify (`api/configs/app_config.py` central settings).

**4. Callback/Hook Manager for LLM Lifecycle (3/5)** — litellm (`integrations/` per-service loggers fired at `success_handler`/`failure_handler`), dify (`api/core/callback_handler/` for streaming), open-webui (Filters/Actions/Pipes/Tools/Skills plugin types).

**5. Async-First with Sync Wrappers (4/5)** — litellm (`asyncify.py`, enforced no raw `requests` in core), mem0 (dual `add()`/`async_add()`), dify (Celery for writes, sync reads), open-webui (`sqlalchemy[asyncio]`, `aiocache`, `aiodns`).

**6. Dual/Layered Caching (3/5)** — litellm (`dual_cache.py`: in-memory L1 + Redis L2, LRU eviction; semantic caches via Qdrant/Redis/Valkey embeddings), dify (Redis embedding cache + scheduled cleanup task), open-webui (`aiocache` + optional Redis).

**7. Middleware/Translation Layer for API Compat (2/5)** — ollama (`middleware/openai.go`, `middleware/anthropic.go` translate to native format), litellm (entire product is this; `passthrough/` for minimal-translation providers).

**8. Repository Pattern for DB Access (2/5)** — litellm (`repositories/*_repository.py` + `unit_of_work.py`), dify (`sqlalchemy_{entity}_repository.py` + `factory.py` for injection).

## How Problems Are Solved

**RAG ingestion vs. retrieval split** — Async writes, sync reads (dify, open-webui):
- dify: upload → Celery `document_indexing_task.py` → chunk (`api/core/rag/`) → embed → vector DB; query-time retrieval is synchronous in-request. Segment-level tasks (`enable/disable/delete_segment_from_index_task.py`) allow incremental index updates without full re-index.
- open-webui: langchain splitters + `sentence-transformers` dense + `rank-bm25` sparse hybrid; optional ColBERT.
- litellm: RAG as library primitive (`litellm/rag/` with `ingestion/`, `text_splitters/`).

**Retrieval quality** — Multi-signal + rerank:
- mem0: semantic + BM25 (with lemmatization) + entity matching scored in parallel, fused in `utils/scoring.py`; pluggable rerankers (Cohere API, HF cross-encoder, LLM-as-reranker, sentence-transformer) with tested fallback behavior; threshold filtering (`threshold: 0.1`).
- open-webui: hybrid dense+BM25.

**Routing/fallbacks** — litellm: model groups with fallback chains (`fallback_utils.py`), pluggable strategies (least-busy/latency/cost), retry backoff headers tested.

**Context window management**:
- ollama: `agent/compactor.go` compacts history near limits
- litellm: `compression/` pipeline (scoring sub-strategies, message stubbing) applied pre-dispatch
- dify: `api/core/memory/` conversation memory

**Cost/token tracking** — litellm: per-provider tokenizers (`tokenizers/`, tested per provider), per-request cost calc (`llm_cost_calc/`), budget enforcement via repository + spend log partitioning (Postgres). open-webui: tiktoken + sentencepiece.

**Streaming** — All 5 repos. litellm: per-API-surface streaming iterators + `sse_output_recovery.py` for partial failures. mem0: fire-and-forget memory write parallel with response streaming:
```typescript
const addTask = addMemories(messages, {user_id});
// ... stream response ...
await addTask; // await at stream end
```

**LLM output parsing robustness** — mem0: dedicated tests `test_json_prompt_fix.py`, `test_chatty_llm_parsing.py`. Prompts centralized in `configs/prompts.py`.

**Sandboxed tool/code execution** — dify (separate Go runtime with Linux landlock + Squid SSRF proxy for all agent HTTP), open-webui (`RestrictedPython`), ollama (approval gates: `agent/approval.go`).

**MCP support** — litellm (`experimental_mcp_client/`, semantic tool filtering, MCP guardrails/hooks), open-webui (`mcp==1.27.2`).

**Hardware/backend selection** — ollama: runtime GPU discovery (`discover/gpu.go`) selects among pre-built llama.cpp binaries (CUDA v12/v13, ROCm, Vulkan, Metal, CPU) rather than runtime linking.

**Prompt engineering workflow** (Anthropic docs): eval-first gate (define success criteria + evals before prompt iteration); use model switch not prompting for latency/cost problems; metaprompt to bootstrap first drafts; per-model prompt guides.

## Architecture Decisions Seen

- **API + Worker split** (dify): Flask API process vs. Celery workers for all ML compute — independent scaling of serving vs. indexing. vs. **monolith** (litellm proxy: single FastAPI app; open-webui: single FastAPI + static SPA).
- **Subprocess isolation for inference** (ollama): Go binary spawns llama.cpp `llama-server` child process — process isolation at IPC cost.
- **GGUF as canonical format** (ollama): all models converted on import; OCI-like layer/manifest storage for distribution.
- **SQL primary + vector DB secondary** (dify, mem0, open-webui): metadata/history in Postgres/SQLite (SQLAlchemy + Alembic), embeddings in pluggable vector store.
- **OSS + managed platform dual-client** (mem0): same interface, local execution vs. HTTP client to platform; three deployment modes from one codebase.
- **Hot path in Rust** (litellm): `litellm-rust/` crates with python-bridge for performance-critical gateway path.
- **LLM-driven extraction vs. rules** (mem0): single-pass ADD-only LLM extraction — flexible but costly/non-deterministic.
- **Enterprise as conditional package** (litellm): separate `enterprise/` pyproject, conditionally imported.

## Testing Approaches

- **Base test contracts per provider type** (litellm): `base_embedding_unit_tests.py`, `base_llm_unit_tests.py`, `base_rerank_unit_tests.py` — new providers must pass shared suites.
- **Static enforcement tests** (litellm): `prevent_key_leaks_in_exceptions.py`, `check_e2e_no_raw_requests.py`, type-error budget (`basedpyright-code-budget.json`), guardrail decorator checks.
- **Reference/golden tests** (ollama): renderer output vs. known-good (`*_reference_test.go`) for chat template correctness; testdata with real model configs.
- **Mock provider APIs in unit tests, separate integration tier** (mem0: pytest-mock + `test_memory_integration.py`; dify: unit / integration / Testcontainers tiers; ollama: co-located unit + `/integration/` package).
- **Behavioral fallback tests** (mem0): reranker fallback doesn't mutate input, respects top_k, logs failures.
- **Load/stress**: litellm router load tests, dify Locust + SSE benchmark, ollama `tools_stress_test.go`, `concurrency_test.go`, `max_queue_test.go`.

## Deployment & Production

- **Docker Compose stacks** (dify: api/worker/web/nginx/vector-DB/ssrf-proxy/sandbox; open-webui: GPU variants).
- **GPU-variant container images** (ollama): multi-stage Dockerfile per backend (cuda_v12/v13, rocm, vulkan, jetpack).
- **Observability**: OpenTelemetry (dify, litellm), Sentry (dify), LLM trace providers — Langfuse/DataDog/LangSmith (litellm `integrations/`, dify `providers/trace/`), Prometheus (litellm), PostHog usage telemetry with sampling (mem0).
- **Scheduled maintenance** (dify Celery beat): embedding cache cleanup, workflow-run log retention, queue-depth monitoring with alerts, provider credential refresh.
- **Secret managers** (litellm): AWS Secrets Manager, Vault, CyberArk.
- **Server lifecycle** (ollama): subprocess health monitoring, restart on failure, Metal-specific retry.
- **Auth**: JWT (mem0 server: httpOnly refresh cookie + body access token; open-webui: JWT + LDAP + OAuth), key management + budget enforcement (litellm proxy).

## Open Questions (for reviewer)

1. **RAG retrieval latency**: dify does sync in-request retrieval (freshness); litellm offers semantic caching (speed/cost). Which default?
2. **Vector DB dependency policy**: mem0 hard-depends on Qdrant; dify/open-webui make all backends optional. Adopt hard default or fully pluggable?
3. **API compat direction**:
