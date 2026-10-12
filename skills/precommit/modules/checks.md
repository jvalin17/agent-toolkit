# Precommit — checks module

Before `git commit` / `git push`:

1. User instructions addressed (diff vs request).
2. Tests meaningful (specific values, would fail if feature deleted).
3. Standards: naming, no secrets, no easy-way-out stubs.
4. App verification when UI involved (user tried locally or smoke).
5. Run project `test_command` / `lint_command` from `gates.json`.
6. Call `finalize_report.py precommit` with findings — do not write `reports/` by hand.

Use `run_function("gate_status", {"project_dir": ".", "skill": "precommit"})` to see missing markers.
