---
role: code-health
sources: 4
synthesized_at: 2026-08-17T02:17:01.623301
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Code-health knowledge synthesized from 4 repos: biomejs/biome (Rust monorepo linter), eslint/eslint (JS layered monolith), openemr/openemr (legacy PHP monolith with modern layers), renovatebot/renovate (TS single-package monorepo). Covers regression prevention, dependency management, tech debt handling, complexity control, and test suite health.

## Patterns Found (ranked by frequency)

### Snapshot Testing for Regression Prevention (3/4: biome, renovate, eslint-adjacent)
- **biome**: `insta` crate; fixture + `.snap` side-by-side in `tests/specs/<group>/<rule>/<scenario>/`; update via `cargo insta review`. Explicit `valid-*`/`invalid-*` scenario split.
- **renovate**: `lib/config/__snapshots__/` for large config-object comparisons via vitest.
- Risk noted (biome): snapshot drift if `.snap` files updated without review.

### Fuzzing (2/4: biome, eslint)
- **biome**: `fuzz/fuzz_targets/rome_parse_*.rs` covering all parsers + formatters, with committed corpus.
- **eslint**: `tools/eslint-fuzzer.js` + `eslump` dev dependency, with runner `tools/fuzzer-runner.js`.

### Build-Time Code Generation with Committed Output (3/4: biome, eslint, renovate)
- **biome**: `.ungram` grammar files → generated syntax nodes via `xtask/codegen`; several `build.rs` files generate from data files.
- **eslint**: lint-staged regenerates configs/types on commit of rule files:
```json
"lib/rules/*.js": [
  "node tools/update-eslint-all.js",
  "node tools/update-rule-type-headers.js",
  "git add packages/js/src/configs/*.js lib/types/rules.d.ts"
]
```
- **renovate**: `tools/generate-imports.mjs` generates module import maps; runs via `pretest`.
- Risk noted (biome): stale-output issues if cache not invalidated.

### Module Registry / Facade Boundaries (3/4: eslint, renovate, biome)
- **eslint**: each subsystem exposes `index.js`; direct internal imports forbidden by lint rule.
- **renovate**: each module type (datasource/manager/versioning/platform) registers in a central `index.ts`.
- **biome**: crate-per-language decomposition (`biome_<lang>_<layer>`) enforces boundaries via Cargo crate graph.

### Workspace Monorepo (3/4: biome, eslint, renovate)
- biome: Cargo workspace + pnpm workspaces, `[workspace.dependencies]` centralizes versions.
- eslint: npm workspaces (`packages/js`, `packages/eslint-config-eslint`).
- renovate: single package; `pnpm-workspace.yaml` only for e2e tests.

### Config Migration Pipeline (2/4: renovate, openemr)
- **renovate**: `lib/config/migrations/` (versioned migration classes) → parse → massage → migrate → validate pipeline.
- **openemr**: 30+ flat SQL files (`sql/2_6_0-to-2_6_1_upgrade.sql`) plus a newer PHP migration framework (`db/Migrations/`) — dual systems coexisting.

### Dead Code Detection (2/4: eslint, biome)
- eslint: `knip.jsonc` + `"lint:unused": "knip"`.
- biome: `[workspace.lints.rust] dead_code = "warn"` across all crates.

## How Problems Are Solved

### PROBLEM: Preventing layer/boundary violations
- **eslint**: lint-time enforcement via `n/no-restricted-require` generated per layer:
```js
function createInternalFilesPatterns(pattern = null) {
    return Object.values(INTERNAL_PATHS)
        .filter(p => p !== pattern)
        .map(p => ({ name: [resolveAbsolutePath(p),
            `!${resolveAbsolutePath(p.replace(/\*\*\/\*$/u, "index.js"))}`] }));
}
```
Gap noted: no runtime enforcement, no dependency-cruiser/madge.
- **biome**: compiler-enforced via crate boundaries (~80 crates).
- **renovate**: typed interfaces + central registration; `ls-lint` enforces file naming.

### PROBLEM: Unstable/experimental features breaking stable contracts
- **biome**: `nursery` rule group — experimental rules explicitly marked, promotion path to stable groups.

### PROBLEM: Known-buggy dependency versions
- **biome**: exact pin with inline rationale: `mimalloc = "=0.1.48"` with comments linking to issues #10270/#11242 (Windows ARM64 crash).
- **eslint**: `ajv` pinned to v6 (v8 has breaking API changes) — long-standing constraint.
- **biome**: `syn = "1.0.109"` (v1 while v2 stable) — proc-macro crates locked to older API.

### PROBLEM: Ecosystem regression detection
- **eslint**: `tools/test-ecosystem/` runs ESLint against external plugins/configs; `test:ecosystem` script.
- **openemr**: `ci/inferno/` runs ONC FHIR certification black-box tests.

### PROBLEM: Test isolation (network/fs)
- **renovate**: `test/http-mock.ts` (nock wrapper) for all HTTP; `memfs` via `__mocks__/fs.ts`; vitest `mockReset: true` globally.
- **eslint**: `proxyquire` for CJS module mocking; sinon for stubs.

### PROBLEM: CI test suite scale
- **renovate**: named test shards via `TEST_SHARD` env var (`tools/test/shards.ts`).
- **openemr**: 14+ Docker Compose matrices (PHP × MySQL × webserver × Redis configs), including dedicated `_upgrade` environments testing migration integrity.

### PROBLEM: Documentation drift
- **renovate**: docs are tested — `test/docs/documentation.spec.ts`, fenced-code syntax checks (`tools/check-fenced-code.ts`), static data JSON files validated against schemas at test time.
- **eslint**: rule message format enforced by lint: `report-message-format: ["error", "^[^a-z].*\\.$"]`.

### PROBLEM: Legacy naming / rename debt
- **biome**: fuzz targets and corpus still use `rome_` prefix post-rename — documented, unresolved.
- **openemr**: `C_*.class.php` / `.inc.php` legacy conventions coexist with PSR-4 `src/`.

## Architecture Decisions Seen

| Decision | Repo(s) | Tradeoff noted |
|---|---|---|
| Crate-per-language decomposition | biome | Independent versioning vs ~80-crate dependency complexity |
| Lint-enforced layers in single package | eslint | No package boundary overhead vs enforcement only if lint runs |
| Single artifact, 90+ modules | renovate | Simple distribution vs monolithic build |
| Strangler pattern (legacy + modern layers) | openemr | Incremental modernization vs dual systems (two config tiers, two migration systems, two templating approaches) |
| Unbundled ESM dist | renovate | Subpath imports/tree-shaking preserved vs many dist files |
| Self-hosting (`"eslint": "file:."`) | eslint | Dogfooding own tool for lint |
| Incremental computation (salsa) | biome | Efficient re-analysis vs API churn (salsa 0.27.x) |
| Multiple overlapping linters (biome + oxlint + tsc + ls-lint + markdownlint) | renovate | Coverage breadth vs 5 tools in one lint script |
| Vendored dependencies (phpGACL, ADODB, Smarty) | openemr | No package-manager updates flow to these — dependency-health blind spot |

## Testing Approaches
- **Test co-location**: renovate (`.spec.ts` beside source) vs mirrored trees: eslint (`tests/lib/**` mirrors `lib/**`).
- **Coverage tooling**: c8 (eslint), v8 provider with explicit per-file exclusions + `skipFull` locally (renovate), kcov+pcov (openemr).
- **Property-based**: quickcheck (biome).
- **Two test runners in one repo**: renovate (vitest + node `--test`).
- **Browser parity testing**: eslint runs same linter test file in Node (mocha) and browser (Cypress against webpack build).
- **Upgrade-path testing**: openemr dedicated `_upgrade` compose environments.
- **Type-level tests**: eslint uses `eslint-plugin-expect-type` on hand-maintained `.d.ts`; separate tsconfigs for legacy TS (5.3) and TS 7 preview compat.
- **Test convention enforcement via lint**: eslint bans `assert.doesNotThrow()` via `no-restricted-syntax`; enforces test-case property ordering.

## Deployment & Production
- **renovate**: OpenTelemetry baked in (8 packages, cloud resource detectors, custom file exporter); Redis + S3 cache backends behind abstraction (`lib/util/cache/package/backend.ts`); strict engine pins (`node ^24.11.0`, `pnpm ^11.0.0`).
- **openemr**: three Dockerfile variants (binary/flex/release); `auto_configure.php` bridges env vars → file config; Redis Sentinel (TLS/mTLS) session variants; `meta/health/index.php` health endpoint.
- **eslint**: file-content-hash lint result caching (`lint-result-cache.js` + `hash.js`), isolated to cli-engine; config-with-functions serialization handled specially for cache keys (`lib/shared/serialization.js`).
- **biome**: `deny.toml` for dependency audit policy; `rust-toolchain.toml` pins toolchain; changesets for release management.

## Open Questions (for reviewer)
1. **Boundary enforcement**: lint-rule-based (eslint) vs compiler/package-based (biome) vs interface-registry (renovate) — which to recommend as default, and is lint-only enforcement sufficient?
2. **Test placement**: co-located specs (renovate) vs mirrored test tree (eslint, biome) — pick one convention?
3. **Snapshot testing scope**: biome uses it as the primary test mechanism; renovate uses it narrowly. Recommend limits on snapshot use?
4. **Dependency pinning style**: exact pin with issue-link comment (biome) vs staying on old major indefinitely (eslint ajv v6, biome syn v1) — is the latter a pattern or an anti-pattern for this role?
5. **Generated code committed to repo** (all of biome/eslint/renovate): treat as accepted practice with regeneration checks, or flag as drift risk?
6. **Multiple overlapping linters** (renovate's 5 tools): thoroughness or maintenance burden?
7. **openemr's dual-system coexistence** (two migration systems, two config tiers): document as strangler-pattern reference or as a tech-
