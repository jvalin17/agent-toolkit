# LLM Integration Architecture

Decisions for integrating Large Language Models into the system. Only relevant when requirements include an LLM Strategy section.

## Inputs

Read `requirements/<name>.md` and extract:
- **LLM Strategy** section — provider choice, use cases, constraints, fallback providers
- **Data sensitivity** — what data can/cannot be sent to external APIs (guardrail G9)
- **Budget constraints** — token/request budgets, cost ceilings
- **Latency requirements** — acceptable response times for LLM-powered features
- **User-facing vs internal** — determines streaming needs, error handling, and safety requirements

Also read the Quick Architecture from `architecture/<name>.md` and any ML/AI Architecture decisions already made.

**Important:** Use the provider choice, use cases, and constraints from requirements as input. Do not re-ask what was already decided.

---

### Decision 1: LLM Provider Architecture

**Context:** How the application communicates with the LLM. The foundational integration decision.

**Options:**

| | Option A: Direct SDK Integration | Option B: Abstraction Layer / Gateway | Option C: Agent Framework | Option D: Local Inference Runtime |
|---|---------|---------|---------|---------|
| What | Use provider SDK directly (Anthropic SDK, OpenAI SDK) | Wrapper layer that abstracts provider details (LiteLLM, AI Gateway, custom) | Framework for complex workflows (LangChain, LlamaIndex, Semantic Kernel, Anthropic Agent SDK) | Self-hosted inference (Ollama, vLLM, llama.cpp) |
| Best for | Simple integrations, single provider, getting started fast | Multi-provider setups, provider switching, fallback chains | Complex chains, RAG, tool use, multi-step agents | Privacy-sensitive, offline, or cost-optimized at scale |
| Trade-off | Tightest coupling, hardest to switch providers | Adds a layer of complexity, potential abstraction leaks | Heaviest abstraction, framework lock-in, harder to debug | Infrastructure complexity, limited to open-source models |
| Cost | Per-token API pricing | Same API pricing + minimal infra for gateway | Same API pricing + framework overhead | GPU/CPU infrastructure cost, no per-token cost |
| SOLID/DRY check | ⚠️ Violates DIP — business logic coupled to provider | ✅ DIP — business logic depends on abstraction | ⚠️ Framework becomes a dependency for everything | ✅ Full control, but more code to maintain |

**If requirements specify a fallback provider:** Design the abstraction layer (Option B) to support failover. Define: primary provider, fallback trigger (timeout, error rate, cost limit), fallback provider, and behavior difference (e.g., fallback may have lower quality).

**Example:** "Direct SDK is simplest but locks you in. An abstraction layer adds complexity but lets you switch providers or add fallbacks. Agent frameworks add more abstraction but handle complex workflows like RAG pipelines and tool use automatically."

**Consequence:** Shapes how prompts are managed, how context is assembled, and how responses are processed.

---

### Decision 2: Prompt Management

**Context:** How prompts are stored, versioned, and tested. Depends on provider architecture (Decision 1).

**Options:**

| | Option A: Inline in Code | Option B: Template Files (Jinja2, Handlebars) | Option C: Prompt Management Platform | Option D (local/cheap): Markdown Files in Repo |
|---|---------|---------|---------|---------|
| What | Prompts as string literals in application code | Prompts in template files, separate from code, with variable injection | Managed platform with versioning and A/B testing (Anthropic Workbench, PromptLayer, Helicone) | Prompts stored as .md files in the repository, loaded at runtime |
| Best for | Simple apps with 1-3 prompts that rarely change | Medium complexity, prompts that evolve independently of code | Large teams, frequent prompt iteration, non-technical editors | Small-medium teams wanting version control without a platform |
| Trade-off | Hard to iterate, prompts buried in logic, no separation | Separate deployment concern, template syntax learning curve | Vendor dependency, cost, integration complexity | Manual loading, no A/B testing built-in |
| Cost | Free | Free | $20-200+/mo | Free |
| SOLID/DRY check | ⚠️ Violates SRP — code and prompts mixed | ✅ Clear separation of concerns | ✅ Full separation + tooling | ✅ Good separation, version controlled |

**Additional decisions:**
- **Who can edit prompts?** Developers only vs product team vs non-technical users. This drives whether you need a UI for prompt editing.
- **For agents/tool use:** How are tool definitions structured and maintained? Inline vs config files vs dynamic registration.
- **Prompt testing:** How do you validate that a prompt change doesn't break things? Golden test sets, regression checks, human eval.

**Consequence:** Affects deployment process (can you update prompts without deploying code?), team workflow, and iteration speed.

---

### Decision 3: Context Management

**Context:** How the application assembles what goes into the LLM. This is where context window budget, retrieval strategy, and conversation history are designed. Depends on provider architecture (Decision 1) and prompt management (Decision 2).

**Options for conversation history:**

| | Option A: Full History | Option B: Sliding Window | Option C: Summarization |
|---|---------|---------|---------|
| What | Send entire conversation to the LLM every turn | Keep only the last N turns | Periodically summarize older turns, keep summary + recent turns |
| Best for | Short conversations, high context fidelity | Long conversations with bounded cost | Very long conversations where history matters |
| Trade-off | Token cost grows linearly, hits context limit | Loses earlier context | Lossy compression, summarization cost and latency |
| Cost | Highest (full history every turn) | Predictable (bounded window) | Moderate (summarization cost + bounded window) |
| SOLID/DRY check | ✅ Simplest | ✅ Simple with clear boundary | ⚠️ Summarization adds complexity |

**Context retrieval (if requirements mention search/documents/knowledge base):**

| | Option A: Vector Search (Embeddings) | Option B: Keyword Search (BM25/TF-IDF) | Option C: Direct Document Injection | Option D: Hybrid (Vector + Keyword) |
|---|---------|---------|---------|---------|
| What | Embed documents and queries, retrieve by semantic similarity | Traditional text search on document content | Directly include relevant documents in the prompt | Combine semantic and keyword search for retrieval |
| Best for | Semantic matching, concept-level retrieval | Exact term matching, known terminology | Small document sets that fit in context | Best retrieval quality, covers both semantic and exact matches |
| Trade-off | Embedding cost, may miss exact matches | Misses semantic similarity | Limited by context window size | Most complex to implement |
| Cost | Embedding API + vector DB | Free (built-in to most search engines) | No additional cost (but uses context budget) | Embedding API + search engine |

**Do not assume RAG is needed.** Present the options and let the user decide based on their data and use case.

**System prompts:** Static (same for all users) vs dynamic (role-dependent, feature-flag-dependent). Define the context window budget: how to split tokens between system prompt, conversation history, retrieved context, and user input.

**Consequence:** Affects token costs, response quality, and the infrastructure needed for retrieval.

---

### Decision 4: Response Handling

**Context:** How the application processes LLM output. Depends on provider architecture (Decision 1) and what the output is used for.

**Options for delivery mode:**

| | Option A: Batch (Complete Response) | Option B: Streaming |
|---|---------|---------|
| What | Wait for full response, then deliver | Stream tokens as they are generated |
| Best for | Background processing, structured output parsing | Chat UIs, user-facing interactions (perceived latency improvement) |
| Trade-off | Higher perceived latency for users | More complex client handling, harder to validate mid-stream |
| Cost | Same API cost | Same API cost |
| SOLID/DRY check | ✅ Simpler processing pipeline | ⚠️ Streaming adds complexity to error handling |

**Options for structured output:**

| | Option A: JSON Mode | Option B: Function/Tool Calling | Option C: Post-Processing (regex/parsing) |
|---|---------|---------|---------|
| What | Request JSON output from the LLM directly | Use provider's function calling to get structured responses | Parse free-text output with regex, XML parsing, or custom logic |
| Best for | Simple structured data extraction | Complex structured interactions, multi-step workflows | Legacy integrations, providers without structured output |
| Trade-off | May not always produce valid JSON | Provider-specific implementation | Fragile, breaks with prompt changes |
| SOLID/DRY check | ✅ Clear output contract | ✅ Strong contract via function definitions | ⚠️ Fragile, hard to maintain |

**Output validation:** Schema validation (Zod, Pydantic), safety filtering, hallucination checks (cross-reference with source data).

**Error handling:** Retries with exponential backoff, fallback to cheaper model, graceful degradation (show cached response or "try again" message).

**Caching:**
- **Exact-match cache:** Same prompt → same response (high hit rate for repetitive tasks)
- **Semantic cache:** Similar prompts → cached response (embedding-based similarity)

**Consequence:** Affects frontend design (streaming requires different UI patterns), error UX, and reliability.

---

### Decision 5: Security & Safety

**Context:** Protecting the application and users from LLM-specific risks. Applies regardless of other decisions. **Must reference OWASP Top 10 for LLM Applications (G-ARCH-3).**

**OWASP LLM Top 10 reference areas:**
- LLM01: Prompt Injection
- LLM02: Insecure Output Handling
- LLM03: Training Data Poisoning
- LLM04: Model Denial of Service
- LLM05: Supply Chain Vulnerabilities
- LLM06: Sensitive Information Disclosure
- LLM07: Insecure Plugin Design
- LLM08: Excessive Agency
- LLM09: Overreliance
- LLM10: Model Theft

**Decisions:**

#### 5a: Prompt Injection Defense

| | Option A: Input Sanitization | Option B: System Prompt Hardening | Option C: Layered Defense |
|---|---------|---------|---------|
| What | Filter/escape user input before including in prompts | Design system prompts to resist manipulation | Combine input filtering, prompt hardening, and output filtering |
| Best for | Simple applications, known input patterns | All applications (baseline defense) | Production applications handling untrusted input |
| Trade-off | May filter legitimate input, cat-and-mouse with attackers | Not foolproof against sophisticated attacks | Most complex, but most robust |
| SOLID/DRY check | ✅ Input validation as separate layer | ✅ Defense in prompt layer | ✅ Defense in depth |

#### 5b: PII Handling

| | Option A: Strip PII Before Sending | Option B: Use Providers with Data Processing Agreements | Option C: Self-Hosted Models |
|---|---------|---------|---------|
| What | Detect and redact PII from prompts, re-inject in responses | Use providers that contractually protect your data | Keep all data on your infrastructure |
| Best for | Sensitive data with external APIs | Enterprise compliance requirements | Maximum data control, regulated industries |
| Trade-off | Detection accuracy, context loss from redaction | Still sending data externally, legal complexity | Infrastructure cost and complexity |
| SOLID/DRY check | ✅ PII filter as separate middleware | ✅ Contractual protection | ✅ Full control |

#### 5c: Rate Limiting & Abuse Prevention
- Per-user token budgets and request throttling
- Anomaly detection for unusual usage patterns
- Cost circuit breakers (stop if daily spend exceeds threshold)

#### 5d: Content Filtering
- Safety classifiers on input (block harmful requests)
- Safety classifiers on output (block harmful responses)
- Custom content policies per use case

#### 5e: Audit Logging

| | Option A: Log Prompts Only | Option B: Log Prompts + Completions | Option C: Full Audit Trail |
|---|---------|---------|---------|
| What | Log what was sent to the LLM | Log both input and output | Log input, output, model version, latency, cost, user ID, and decisions made |
| Best for | Debugging, basic monitoring | Quality assurance, content review | Regulated industries, compliance, incident investigation |
| Trade-off | Can't review outputs | Storage cost for completions | Highest storage cost, PII in logs risk |
| Retention | 30 days typical | 90 days typical | Per regulatory requirement |
| SOLID/DRY check | ✅ Minimal logging | ✅ Comprehensive | ⚠️ Must handle PII in logs carefully |

**Consequence:** Security decisions affect the entire LLM integration pipeline — from input processing to response delivery to storage.

---

## Decision Format Reference

Each decision above follows the standard format from the base SKILL.md. For guardrails (G-ARCH-1 through G-ARCH-4, G1-G9), see `shared/guardrails.md` — they are not duplicated here. G-ARCH-3 (OWASP LLM Top 10 reference) is directly addressed in Decision 5.
