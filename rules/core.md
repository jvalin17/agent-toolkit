# Core development rules

1. **Stub first, pull depth** — follow the short skill stub; call `get_module` only when the pull map says so.
2. **TDD for logic** — write/adjust a failing test before production code. Use `run_function("check_tdd_order")` before editing source if unsure.
3. **Plan before new work** — show an execution plan for non-trivial changes; wait for approval when required.
4. **Precommit before commit** — never `git commit` / `git push` without `/precommit` (or `run_function("gate_status")` ready).
5. **No false done** — verify tests and behavior; do not claim fixed without evidence.
6. **Host-agnostic policy** — same quality bar on every LLM; only transport (hooks vs CLI) differs.
