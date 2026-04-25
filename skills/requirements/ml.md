# ML/AI Requirements Gathering

Sub-skill for the requirements agent. Covers ML problem type, algorithm preferences, data sources, quality targets, and operational constraints. Triggered when the user selected "Machine learning / AI" in intake Q5.

Follow G-REQ-3 (ML data privacy) throughout: flag PII in training data and compliance needs for regulated industries.

Enter this flow with: "Let's figure out the intelligence layer."

Use AskUserQuestion tool for all batches.

---

## Batch 1: ML Problem Type

**Q-ML-1: What kind of ML/AI capability do you need?** (multi-select)
- Recommendations (suggest items, content, people)
- Predictions / forecasting (predict outcomes, demand, risk)
- Classification (spam detection, sentiment, categorization)
- Natural language processing (text understanding, summarization, extraction)
- Computer vision (image recognition, object detection, OCR)
- Generative AI (text generation, image generation, code generation)
- Search / ranking (semantic search, relevance scoring)
- Anomaly detection (fraud, system health, outliers)
- Something else (describe it)

**Q-ML-2: Are you building a model or using an existing one?**
- Train a custom model (need training data, infrastructure)
- Fine-tune a pre-trained model (need some training data, less infrastructure)
- Use an API / hosted model (OpenAI, Claude, HuggingFace, etc.) (need API integration)
- I don't know (show best option: "For most apps, start with an API. Train custom only when you need domain-specific accuracy or data privacy.")

---

## Batch 1b: Algorithm & Model Preferences

Only enter this batch when the user selected "Train a custom model" or "Fine-tune a pre-trained model" in Q-ML-2. Skip if they selected "Use an API / hosted model".

**Q-ML-ALG-1: Do you have a specific algorithm or model architecture in mind?**
- Yes, I know what I want (ask which one)
- I have a general direction but need guidance
- No, recommend based on my problem
- I'm not sure what's available

**If user names a specific algorithm or architecture**, present a quick assessment:

> - **What it is:** [one-sentence explanation]
> - **Good fit for your problem?** [yes / partial / no — with reasoning]
> - **Data requirements:** [what kind and how much data it typically needs]
> - **Complexity:** [low / medium / high — training, tuning, infrastructure]
> - **Alternative to consider:** [if there's a simpler or better-suited option]

For the full table of algorithm families (classical ML, neural networks, deep learning, RL, recommendations, time series, graph neural networks, clustering), see `references/ml-algorithms.md`. Use that table to validate the user's choice and suggest alternatives.

### Scope Check

Some ML approaches require specialized expertise, hardware, or infrastructure that may be outside scope. If the user's choice falls into this category:

> "This is a valid approach, but implementing [algorithm] from scratch requires [specialized GPU infrastructure / extensive ML engineering / large labeled datasets / etc.]. Here's what I'd recommend:"

**If we can still help:**
- "We can set up the project structure, data pipeline, and training loop. You'll need ML expertise for model tuning and evaluation."
- "We can integrate a pre-trained version of this via [library/API]. Training from scratch is a separate effort."

**If it's truly out of scope**, see the out-of-scope guidance in `references/ml-algorithms.md` for frameworks, managed platforms, learning resources, model hubs, and communities to point the user toward.

Note in the requirements doc: "User wants [algorithm]. Implementation requires [what]. Recommended path: [suggestion]."

---

## Batch 2: Data & Quality

**Q-ML-3: What data will the model use?**
- User behavior data (clicks, purchases, views)
- Text data (documents, messages, reviews)
- Image / video data
- Structured data (tables, databases, CSVs)
- Real-time streaming data
- I don't have data yet (note: will need a data collection strategy)

**Q-ML-4: How accurate does it need to be?** (explain with examples)
- Best effort — wrong sometimes is OK (recommendations, content suggestions)
- Mostly right — occasional errors acceptable (search ranking, categorization)
- Highly accurate — errors have consequences (medical, financial, safety)
- Near-perfect — errors are unacceptable (autonomous systems, critical decisions)

> Show: "Higher accuracy = more data + more compute + more iteration. At 'highly accurate' level, expect significant investment in data labeling and model evaluation."

At this point, apply G-REQ-3: if the data involves PII (user behavior, messages, health records, financial data), flag it explicitly and ask about compliance requirements (GDPR, HIPAA, etc.).

---

## Batch 3: Operational Concerns (Standard + System Design modes only)

Skip in Quick mode.

**Q-ML-5: How will users interact with the ML component?**
- Real-time — instant responses (< 200ms, e.g., autocomplete, recommendations)
- Near-real-time — fast but not instant (< 2s, e.g., image analysis, translation)
- Batch — process offline, results available later (e.g., nightly reports, bulk classification)
- Background — runs continuously, surfaces results when relevant (e.g., anomaly alerts)

**Q-ML-6: Any constraints on the ML component?**
- Data must stay on-premise / in specific region (privacy, compliance)
- Must work offline / on-device
- Cost ceiling for API calls (what's the budget?)
- Must be explainable (users need to understand WHY)
- Must be auditable (regulated industry)
- No constraints

**If user is confused about ML approach:** Launch a sub-agent to research:

> "Let me research how similar products use ML for [feature] — one moment."

Spawn Agent tool with: "Research how [similar products] implement ML for [feature]. Return: what model type they use, training data approach, accuracy levels, whether they use APIs or custom models. Keep it concise — 5-10 bullet points."

---

## Output Section Template

Add this section to the requirements document:

```markdown
## ML/AI Requirements

### ML Capabilities
| Capability | Type | Model Approach | Priority |
|-----------|------|---------------|----------|
| ... | classification/NLP/etc. | API/custom/fine-tune | must/should/could |

### Data Requirements
| Data Source | Type | Volume | Available? |
|-----------|------|--------|-----------|
| ... | text/image/structured | estimate | yes/no/partial |

### Quality Targets
- **Accuracy level:** [best-effort / mostly-right / highly-accurate / near-perfect]
- **Latency target:** [real-time / near-real-time / batch / background]

### Constraints
- [constraint 1]
- [constraint 2]

### Algorithm / Model Preference (if applicable)
- **User's choice:** [algorithm or architecture name]
- **Fit assessment:** [good fit / partial / not recommended — with reasoning]
- **Implementation path:** [we can implement / need pre-trained model / out of scope]
- **Recommended framework:** [PyTorch / TensorFlow / scikit-learn / HuggingFace / etc.]
- **Out-of-scope notes:** [if applicable — what the user needs beyond this toolkit]

### Model Evaluation Criteria
- [how success is measured — accuracy, precision, recall, F1, user satisfaction]
```
