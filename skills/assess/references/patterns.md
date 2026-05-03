# Modern Patterns — When They're Appropriate vs Overkill

> Keep updated by /updater. Last verified: 2026-05-03

## AI/ML Patterns

### RAG (Retrieval Augmented Generation)
- **What:** Retrieve relevant docs from corpus, inject into LLM prompt for grounded answers
- **Use when:** Corpus exceeds context window, or cost/latency of full context is too high
- **Overkill when:** Under ~50 pages with modern long-context model (1M tokens). Just stuff it in the prompt.
- **Scale:** Matters when corpus > context window size. With 1M-token windows, threshold is much higher than 2023.

### GraphRAG
- **What:** Extract entities and relationships into knowledge graph, traverse for retrieval
- **Use when:** Queries need cross-document relationship reasoning ("how does X relate to Y across the dataset")
- **Overkill when:** Simple FAQ, single-document Q&A. Basic RAG with re-ranking handles 2-3 doc queries.
- **Scale:** Query complexity threshold, not data size. If users ask relationship questions, consider it.

### Vector Databases
- **What:** Store embeddings for similarity search
- **Use when:** Semantic search on >100K vectors
- **Overkill when:** <10K documents (brute-force in-memory is fine), or keyword search with good tokenization suffices
- **Thresholds:** In-memory (numpy/faiss) < 100K. pgvector < 5-10M. Pinecone/Qdrant > 10M.

### MCP (Model Context Protocol)
- **What:** Standard protocol for LLM apps to connect to external tools/data
- **Use when:** Multiple external integrations (3+), or building a product AI agents should connect to
- **Overkill when:** Single LLM calling single API. Simple function call suffices.

### Multi-Agent / Sub-Agents
- **What:** Multiple specialized agents with isolated contexts
- **Use when:** 3+ distinct domains competing for context, parallel execution needed
- **Overkill when:** Linear workflow, single domain. Token cost 4-220x higher (avg 15x).
- **Scale:** Coordination gains plateau at 4 agents. Default to single agent.

### Context Engineering
- **What:** Designing what goes into the LLM context — retrieval, memory, token budget, ordering
- **Always relevant.** Smart context engineering reduces costs 50-90%.
- **Key insight:** Every model has a Maximum Effective Context Window far below advertised. Put critical info at start and end (primacy/recency bias).

### Chain-of-Thought
- **Use when:** Complex multi-step reasoning, models >100B parameters
- **Overkill when:** Simple classification/extraction, modern reasoning models (o3/o4). Adds 20-80% latency for 2-3% gain on simple tasks.

## Infrastructure Patterns

### Caching (Redis, CDN, in-memory)
- **Threshold:** >100 QPS per endpoint
- **Below threshold:** Database handles it fine

### Connection Pooling
- **Threshold:** Always for server apps (even low traffic). Each Postgres connection = ~1.3MB.

### Load Balancer
- **Threshold:** >100 QPS or >1 server instance

### Microservices
- **Threshold:** >8-10 engineers or >2 teams on same codebase
- **Below threshold:** Well-structured monolith is faster to develop, deploy, debug

### PostgreSQL over SQLite
- **Threshold:** >1 server, concurrent writes, network access needed
- **SQLite is fine for:** Single-machine, single-writer, <100GB, surprisingly high read concurrency

## Data Patterns

### Database Indexes
- **Threshold:** >10K rows on filtered/joined columns retrieving <15% of rows
- **Below threshold:** Full table scans are fast enough

### N+1 Query Fixes
- **Threshold:** Always. Even 10 items = 11 queries vs 2. Correctness issue.

### Vector Search over Keyword Search
- **Threshold:** >50K documents of unstructured data where semantic understanding matters
- **Below threshold:** Keyword search with good tokenization works
