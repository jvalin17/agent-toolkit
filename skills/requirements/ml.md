# ML/AI Requirements Gathering
Keywords: ML, AI, algorithm, model, training, data, accuracy, inference

Sub-skill for the requirements agent. Triggered when user selected "Machine learning / AI" in intake Q5.

Follow G-REQ-3 (ML data privacy) throughout: flag PII in training data and compliance needs for regulated industries.

Enter this flow with: "Let's figure out the intelligence layer."

## Batch 1: ML Problem Type

**Q-ML-1: What kind of ML/AI capability do you need?** (recommendations, predictions, classification, NLP, computer vision, generative AI, search/ranking, anomaly detection, something else)

**Q-ML-2: Are you building a model or using an existing one?** (train custom, fine-tune, use API, don't know — recommend API first)

## Batch 1b: Algorithm & Model Preferences

Only if user selected "Train custom" or "Fine-tune" in Q-ML-2.

**Q-ML-ALG-1: Do you have a specific algorithm or model architecture in mind?**

If user names one, present quick assessment: fit for problem, data requirements, complexity, alternative to consider. See `references/ml-algorithms.md` for the full table.

### Scope Check

If the user's choice requires specialized expertise/hardware outside scope:
- If we can help partially: "We can set up the project structure, data pipeline, and training loop. You'll need ML expertise for model tuning."
- If truly out of scope: point to frameworks, managed platforms, and communities in `references/ml-algorithms.md`.

Note in requirements doc: "User wants [algorithm]. Implementation requires [what]. Recommended path: [suggestion]."

## Batch 2: Data & Quality

**Q-ML-3: What data will the model use?** (user behavior, text, image/video, structured, streaming, no data yet)

**Q-ML-4: How accurate does it need to be?** (best effort, mostly right, highly accurate, near-perfect — with cost implications)

Apply G-REQ-3: if data involves PII, flag and ask about compliance (GDPR, HIPAA, etc.).

## Batch 3: Operational Concerns (Standard + System Design modes only)

**Q-ML-5: How will users interact with the ML component?** (real-time <200ms, near-real-time <2s, batch, background)

**Q-ML-6: Any constraints?** (data residency, offline, cost ceiling, explainability, auditability)

If user is confused: launch sub-agent to research how similar products use ML for their feature.

## Output Section Template

Add to requirements document: ML Capabilities table, Data Requirements table, Quality Targets, Constraints, Algorithm/Model Preference (if applicable), Model Evaluation Criteria.
