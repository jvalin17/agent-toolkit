# LLM Provider Reference

> Reference data — presented to user when exploring LLM strategy. May need periodic updates.
> Last verified: 2026-04-24

---

## Commercial APIs (require API key + pay per use)

| Provider | Models | Best For | Pricing Model |
|----------|--------|----------|--------------|
| Anthropic | Claude (Opus, Sonnet, Haiku) | Complex reasoning, long context, code, safety | Per token (input + output) |
| OpenAI | GPT-4o, GPT-4o-mini, o1/o3 | General purpose, vision, function calling | Per token |
| Google | Gemini (Pro, Flash, Ultra) | Multimodal, large context, Google ecosystem | Per token (generous free tier) |
| Mistral | Mistral Large, Small, Codestral | European hosting, code, multilingual | Per token |
| Cohere | Command R+, Embed, Rerank | RAG, search, enterprise | Per token |

## Free / Open-Source (self-hosted, no API key needed)

| Model | Sizes | Best For | Run Locally With |
|-------|-------|----------|-----------------|
| Llama 3 (Meta) | 8B, 70B, 405B | General purpose, fine-tuning | Ollama, vLLM |
| Mistral / Mixtral | 7B, 8x7B | Fast inference, multilingual | Ollama, vLLM |
| Phi-3 (Microsoft) | 3.8B, 14B | Small/edge devices, mobile | Ollama, ONNX |
| Gemma (Google) | 2B, 7B, 27B | Lightweight, on-device | Ollama, MediaPipe |
| Qwen (Alibaba) | 7B, 72B | Multilingual, code | Ollama, vLLM |

## Free API Tiers (API-based but no cost to start)

| Provider | Free Tier | Limits |
|----------|-----------|--------|
| Google Gemini | Free tier available | Rate-limited, limited models |
| HuggingFace Inference | Free for many models | Rate-limited, cold starts |
| Groq | Free tier | Rate-limited, select models |
| Together AI | Free credits on signup | Limited credits |
