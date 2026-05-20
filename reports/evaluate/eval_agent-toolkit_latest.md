# Evaluation: agent-toolkit (latest)
# Score: **88%** (B+)

**Evaluated:** 2026-05-20  
**Commit:** `103f6d3`  
**Full report:** `eval_agent-toolkit_103f6d3.md`

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Completeness | 80% | 30% | 24.0 |
| Code Quality | 85% | 25% | 21.3 |
| Security | 95% | 20% | 19.0 |
| Test Quality | 91% | 15% | 13.7 |
| Efficiency | 92% | 10% | 9.2 |
| **Overall** | | | **88%** |

## Grade: B+ (85–89%)

---

## Executive summary

Independent re-evaluation at `103f6d3`: core product claims hold (13 skills, 9 agents, 8 hooks, legacy-default gates, green **16/16** pytest + **55/55** hook tests, CI `agent-toolkit-gate` success). Score **below 95%** due to README guardrail count inconsistency (19 vs 17), **G-SESSION-1** missing from `shared/guardrails.md`, stale **`project-state.md`**, and **`hooks/gates.json`** schema drift vs template.

**Do not unlock evaluate gate for 95% push threshold on this score alone.**

---

## Top fixes for 95%

1. Unify README guardrail counts (`README.md:9` vs `:51`).
2. Add G-SESSION-1 section to `shared/guardrails.md`.
3. Update `project-state.md` post–eval follow-ups.
4. Align `hooks/gates.json` with `templates/gates.json`.

**Tests:** `python3 -m pytest tests/test_gate.py -q` → 16 passed; `bash tests/test-hooks.sh` → 55 passed.
