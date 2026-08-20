---
role: data-scientist
sources: 5
synthesized_at: 2026-08-17T01:45:09.856748
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Knowledge synthesized from 5 scientific Python libraries: pandas (data manipulation), scikit-learn (ML prototypes/metrics), statsmodels (statistics/inference), seaborn (visualization), and evidently (evaluation/drift monitoring). Together they cover the DS role's scope: statistical testing, experiment analysis, model evaluation, metrics, and visualization.

## Patterns Found (ranked by frequency across repos)

**1. Result/Display Object Pattern** (statsmodels, sklearn, evidently, pandas)
Computation returns a structured object with named attributes, not raw values:
```python
result = OLS(y, X).fit()
result.params; result.pvalues; result.conf_int(); result.summary()  # statsmodels
RocCurveDisplay.from_estimator(clf, X_test, y_test)                  # sklearn
Report([DataDriftPreset()]).run(current, reference)                  # evidently
```
statsmodels splits Model (data+spec) from Results (post-estimation) classes.

**2. Strategy Pattern for interchangeable stat backends** (all 5)
- seaborn `_stats/` — stat classes share `__call__(data, groupby, orient, scales)`
- sklearn `_loss/loss.py` — swappable loss objects
- pandas `core/computation/engines.py` — numexpr vs python eval
- statsmodels `base/covtype.py` — HC0–HC3, HAC, cluster SEs via `cov_type=` param
- evidently — stat test registry (KS, chi-square, PSI, Wasserstein) selected by name

**3. Registry/String-Dispatch Pattern** (sklearn, evidently, seaborn)
```python
scoring='roc_auc'                    # sklearn: string → scorer via _scorer.py
palettes.color_palette("hls")        # seaborn: facade dispatch
TYPE_ALIASES[alias] → import_string  # evidently: dynamic metric discovery
```

**4. Context Manager for Scoped Config** (seaborn, pandas, sklearn)
```python
with color_palette(pal): ...         # seaborn — restores on exit
with pd.option_context('display.max_rows', 10): ...
with sklearn.config_context(assume_finite=True): ...
```

**5. Consistent Estimator API** (sklearn, statsmodels)
`fit()/predict()/transform()` contract enables generic pipelines, CV, grid search.

**6. Preset/Bundle Pattern** (evidently, seaborn)
Named bundles of many components: `DataDriftPreset`, seaborn themes/contexts.

**7. Vendoring small dependencies** (seaborn `external/` — husl, kde; sklearn `externals/` — array_api_compat, numpydoc) to avoid transitive dependency conflicts.

## How Problems Are Solved

**A/B testing & proportion tests** → statsmodels only:
`stats/proportion.py`: `proportions_ztest()`, `proportion_confint()` (Wilson, Clopper-Pearson); `stats/power.py` for power/sample-size (TTestPower, NormalIndPower).

**Multiple testing correction** → statsmodels `stats/multicomp.py`: `multipletests()` (Bonferroni, Holm, BH, BY), `fdrcorrection()`, `local_fdr()`.

**Confidence intervals** — three approaches:
- Parametric: statsmodels `result.get_prediction(X).summary_frame()` → mean, se, obs_ci bounds
- Bootstrap: seaborn `algorithms.py` (non-parametric CI for plots); statsmodels mediation with bootstrap CIs
- Migration note: seaborn moved `ci=95` → `errorbar=("ci", 95)` (also supports SE, SD, PI) via `_deprecate_ci` shim

**Model comparison / significance testing** → sklearn: `cross_validate` returns train/test scores + timings; `permutation_test_score` for significance; `examples/model_selection/plot_grid_search_stats.py` shows statistical tests on CV results.

**Drift detection** → evidently: reference vs current dataset comparison; thresholds auto-derived from reference distribution (zero-config); statsmodels/scipy stat tests underneath.

**Hyperparameter search** → sklearn: `GridSearchCV`, `RandomizedSearchCV` (samples scipy.stats distributions), `HalvingGridSearchCV` (early elimination).

**Feature importance** → sklearn offers both `feature_importances_` (model-internal) and `permutation_importance()` (model-agnostic, less biased for correlated features — see `plot_permutation_importance_multicollinear.py`).

**Threshold tuning** → sklearn `TunedThresholdClassifierCV` — tunes decision threshold via CV on a business metric.

**Robust standard errors** → statsmodels: `OLS(y,X).fit(cov_type='HC3')` or `cov_type='cluster', cov_kwds={'groups': g}` — post-hoc, no refit needed.

**Missing data** → pandas (`fillna`, `interpolate`, NA-aware nanops); statsmodels `imputation/mice.py` (MICE), `bayes_mi.py`.

**KDE/nonparametrics** → statsmodels `nonparametric/` (bandwidth selection: Scott, Silverman, CV; LOWESS); seaborn vendored scipy KDE to avoid hard scipy dep.

**Diagnostics & influence** → statsmodels: Cook's distance, DFFITS, leverage (`OLSInfluence`); Q-Q plots (`graphics/gofplots.py`); Breusch-Pagan, Ljung-Box (`stats/diagnostic.py`).

**Causal/treatment effects** → statsmodels `treatment/treatment_effects.py` (ATE/ATT via IPW, doubly-robust); mediation analysis.

**LLM evaluation** → evidently only: descriptors (text length, BERTScore, LLM-as-judge via OpenAI/LiteLLM), decorator-based guardrails.

**EDA visualization** → seaborn (FacetGrid/PairGrid composition; grammar-of-graphics `so.Plot` objects API); pandas `df.plot()`, scatter matrix, autocorrelation/lag plots; sklearn Display objects composable on shared axes.

## Architecture Decisions Seen

| Decision | Choice | Repos | Tradeoff |
|---|---|---|---|
| Hot paths | Cython, Python API on top | pandas, sklearn, statsmodels | 10–100x speed vs build complexity |
| Build system | Meson + meson-python | pandas, sklearn, statsmodels | Reliable Cython builds vs contributor friction |
| Heavy stats deps | Optional (`seaborn[stats]`, sklearn extras) | seaborn, sklearn, evidently | Lightweight install vs feature gating |
| Dual APIs | Keep old + new in parallel | seaborn (classic vs objects), statsmodels (patsy + formulaic), evidently (legacy/future dirs) | Backward compat vs maintenance burden |
| Experimental code | Explicit staging areas | sklearn (`experimental/` opt-in imports), statsmodels (`sandbox/`, `archive/`) | Signals instability vs discoverability |
| Bad-practice blocking | seaborn raises `ValueError` for perceptually-misleading palettes ("jet") | seaborn | Opinionated guardrails vs flexibility |
| DataFrame interop | narwhals abstraction (pandas/polars-agnostic) | sklearn | Future-proofing vs extra layer |
| Copy semantics | Copy-on-Write | pandas | Safety vs in-place performance |

## Testing Approaches

**Numerical verification against references** (statsmodels — dominant pattern): compare against R/Stata/NIST certified values:
```python
assert_allclose(result.pvalues, reference_pvalues, rtol=1e-5)
assert_almost_equal(result.params, [known_val], decimal=4)
```

**Numerical assertion helpers** (pandas, seaborn): `tm.assert_frame_equal` (with `rtol/atol`), `npt.assert_array_almost_equal`, `npt.assert_array_less` (ordering).

**Warnings-as-errors** (pandas, statsmodels): pytest `filterwarnings = ["error"]` with explicit allowlists; pandas bans `pytest.warns` in favor of `tm.assert_produces_warning`.

**Contract testing** (sklearn): `check_estimator()` runs on all public estimators — validates API compliance automatically.

**Property-based testing** (pandas): Hypothesis strategies for arbitrary indexes/DataFrames.

**Heavy parametrization** (all): `@pytest.mark.parametrize` over dtypes, backends, engines.

**Test markers for selective runs**: `slow`, `network`, `smoke`, `matplotlib`, `example` (statsmodels, pandas, evidently).

**Notebook/example tests**: statsmodels runs example notebooks as integration tests; sklearn validates docstring parameter consistency.

**Benchmarking**: ASV (airspeed velocity) for performance regression (sklearn, pandas).

**Network isolation**: seaborn's `_network` decorator skips tests when offline; CI pre-caches datasets.

## Deployment & Production

Mostly out of DS role scope. Observable facts:
- 4/5 repos are pure libraries: deployment = PyPI/conda wheels via `cibuildwheel`
- evidently is the exception: optional Litestar HTTP monitoring service, Docker/docker-compose with Grafana dashboards, SQLite/Postgres/S3 storage — but core evals run as pure Python without a server (relevant boundary: DS uses the library; the service is ops territory)
- Versioning from git tags (versioneer/setuptools_scm)

## Open Questions (for reviewer)

1. **Bootstrap vs parametric CIs**: seaborn defaults to bootstrap for plot aggregations; statsmodels uses parametric formulas. Which is the role's default recommendation?
2. **Formula interface**: statsmodels ships both patsy (legacy) and formulaic (new). Standardize on one for new work?
3. **Drift testing**: use evidently's preset/registry approach or call scipy/statsmodels tests directly? Evidently adds zero-config thresholds but a heavier dependency.
4. **Visualization API**: seaborn classic function API vs objects (`so.Plot`) API — which to prefer for new analyses?
5. **Feature importance default**: permutation importance (model-agnostic, slower) vs model-internal — sklearn provides both; pick a house standard?
6. **Warnings policy**: adopt warnings-as-errors in experiment test suites (pandas/statsmodels pattern), or keep permissive for prototyping speed?
7. **LLM evaluation**: evidently's descriptors/LLM-judge patterns are the only source here — sufficient basis for adoption, or needs more evidence?
