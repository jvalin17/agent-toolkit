# ML/Data Implementation

Implement ML models, data pipelines, feature engineering, training, inference, and data validation using TDD.

## Inputs

Read from upstream docs before writing any code. Follow upstream decisions without re-deciding:
- **Algorithm / model** (from requirements doc): If the user chose a specific algorithm (e.g., XGBoost, ResNet, LSTM), use it. Do not suggest alternatives.
- **Framework** (from requirements doc): If a framework was recommended (PyTorch, TensorFlow, scikit-learn, HuggingFace), use it.
- **Model serving** (from architecture doc): Follow the decided approach — API-based, self-hosted, or edge.
- **ML pipeline** (from architecture doc): Follow the decided pipeline architecture — notebooks, Airflow, managed service, etc.
- **Accuracy targets** (from requirements doc): Use these as your test thresholds.
- **Data sources** (from requirements doc): Implement data loading for the specified sources.

## TDD Pattern: Data Contracts First, Then Model Behavior

```
1. DATA CONTRACT TEST — Define expected input/output shapes, types, ranges
2. VALIDATE DATA — Implement data validation (schema, nulls, ranges)
3. MODEL BEHAVIOR TEST — Define expected model behavior (accuracy thresholds from requirements, output shapes)
4. IMPLEMENT MODEL — Build the model using the specified algorithm and framework
5. INTEGRATION TEST — End-to-end: raw data -> pipeline -> model -> prediction
```

## What to Test

- [ ] Data schema: correct types, no unexpected nulls, values in valid ranges
- [ ] Data transforms: input to output matches expected
- [ ] Model output shape: correct dimensions, types
- [ ] Model behavior: meets accuracy/F1 targets from requirements (or reasonable defaults if unspecified)
- [ ] Determinism: seeded randomness produces reproducible results
- [ ] Edge cases: empty input, single sample, very large input
- [ ] Drift detection: model performs consistently over time (if requirements specify monitoring)

For guardrails and core principles, see the main `SKILL.md`.
