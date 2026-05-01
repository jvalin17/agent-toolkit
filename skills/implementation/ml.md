# ML/Data Implementation
Keywords: ML, model, training, inference, data pipeline, feature engineering, validation

Implement ML models, data pipelines, feature engineering, training, inference, and data validation using TDD.

## Inputs

Read from upstream docs before writing any code. Follow upstream decisions without re-deciding:
- **Algorithm / model** (from requirements doc): use the specified algorithm. Do not suggest alternatives.
- **Framework** (from requirements doc): use the specified framework.
- **Model serving** (from architecture doc): follow the decided approach.
- **ML pipeline** (from architecture doc): follow the decided pipeline architecture.
- **Accuracy targets** (from requirements doc): use as test thresholds.
- **Data sources** (from requirements doc): implement data loading for specified sources.

## TDD Pattern: Data Contracts First, Then Model Behavior

```
1. DATA CONTRACT TEST — Define expected input/output shapes, types, ranges
2. VALIDATE DATA — Implement data validation (schema, nulls, ranges)
3. MODEL BEHAVIOR TEST — Define expected model behavior (accuracy thresholds from requirements)
4. IMPLEMENT MODEL — Build using the specified algorithm and framework
5. INTEGRATION TEST — End-to-end: raw data -> pipeline -> model -> prediction
```

For guardrails and core principles, see the main `SKILL.md`.
