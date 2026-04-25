# LLM Strategy Requirements Gathering

Sub-skill for the requirements agent. Covers LLM provider selection, use cases, and integration constraints. Triggered when the user selected Generative AI, NLP, or "Use an API / hosted model" in the ML batches, or named an LLM-based architecture (transformers, GPT fine-tuning, BERT, etc.).

Follow G9 (LLM data security) throughout: flag data that should not be sent to external APIs.

Enter this flow with: "Since you're looking at LLM integration, let me help you pick the right approach."

Use AskUserQuestion tool for all questions.

---

## Provider Preference

**Q-ML-LLM-1: Do you have a preference for an LLM provider?** (select one or more)
- I want to use a specific provider (which one?)
- I want the best quality regardless of cost
- I want the cheapest option
- I want something free / open-source
- I want to run it locally (privacy, offline, no API costs)
- No preference — help me decide

Present the provider reference tables from `references/llm-providers.md` to help the user compare options. Show the relevant table(s) based on their selection:
- "Best quality" or "specific provider" -> show commercial APIs table
- "Cheapest" or "free" -> show free/open-source table and free API tiers table
- "Run locally" -> show free/open-source table
- "No preference" -> show all three tables

At this point, apply G9: if the user's data includes sensitive information (PII, health records, financial data, proprietary business logic), flag it:

> "Note: sending [data type] to external APIs means that data leaves your infrastructure. Consider:"
> - Self-hosted / local models for maximum privacy
> - Providers with data processing agreements (DPAs)
> - Anonymizing or redacting sensitive fields before sending

---

## LLM Use Cases

**Q-ML-LLM-2: What will the LLM do in your app?** (multi-select)
- Chat / conversational interface
- Content generation (emails, summaries, reports)
- Data extraction / parsing (unstructured to structured)
- Code generation / assistance
- Search / RAG (answer questions from your documents)
- Classification / routing (categorize inputs, route requests)
- Translation / localization
- Agents / tool use (LLM calls functions, takes actions)
- Something else (describe it)

---

## LLM Constraints

**Q-ML-LLM-3: Any LLM-specific constraints?**
- Must support function/tool calling
- Must support streaming responses
- Must handle long context (how long? documents, codebases, conversation history)
- Must support vision / multimodal (images, PDFs)
- Must support structured output (JSON mode)
- Response latency matters (time-to-first-token critical?)
- Must work in a specific region (data residency)
- No constraints

---

## Output Section Template

Add this section to the requirements document (nested under ML/AI Requirements or as a standalone section if no other ML is involved):

```markdown
### LLM Strategy

#### Provider
- **Primary:** [provider + model]
- **Fallback:** [provider + model, or "none"]
- **Type:** [commercial API / open-source self-hosted / local]
- **Auth required:** [yes — API key / no — self-hosted]

#### LLM Use Cases
| Use Case | Capability Needed | Latency Requirement |
|----------|------------------|-------------------|
| ... | chat/extraction/RAG/etc. | real-time/batch |

#### LLM Constraints
- [constraint 1 — e.g., must support tool calling]
- [constraint 2 — e.g., data residency in EU]

#### Data Security Notes
- [what data is sent to the LLM]
- [any anonymization or redaction needed]
- [compliance considerations]
```
