# LLM Strategy Requirements
Keywords: LLM, provider, API, Claude, GPT, Gemini, Ollama, tokens, prompts, AI integration

Triggered when user selected Generative AI, NLP, or "Use an API/hosted model." Follow G9 (LLM data security).

**Rules from real usage:**
- Three LLM modes are first-class. For EACH LLM capability, specify behavior in: (1) no-LLM mode (pure algorithmic fallback), (2) offline-LLM mode (local model like Ollama), (3) online-LLM mode (cloud API). Don't treat offline as an afterthought.
- Token budget management is a shared concern. When multiple features use LLMs, require: max tokens per session, priority queue for what gets LLM vs algorithmic processing, never exceed budget without permission.
- Domain knowledge that changes over time (e.g., ATS rules, formatting standards) should be stored as updatable config files, not hardcoded.

---

## Provider Preference

**Q-ML-LLM-1: Do you have a preference for an LLM provider?** (specific provider, best quality, cheapest, free/open-source, run locally, no preference)

Present provider reference tables from `references/llm-providers.md` based on selection. Apply G9 for sensitive data — flag data leaving infrastructure and suggest local models, DPAs, or redaction.

## LLM Use Cases

**Q-ML-LLM-2: What will the LLM do in your app?** (chat, content generation, data extraction, code generation, search/RAG, classification, translation, agents/tool use, something else)

## LLM Constraints

**Q-ML-LLM-3: Any LLM-specific constraints?** (function calling, streaming, long context, vision/multimodal, structured output, latency, data residency, none)

## Output Section Template

Add to requirements document: Provider (primary + fallback + type), LLM Use Cases table, LLM Constraints, Data Security Notes.
