---
role: android
sources: 5
synthesized_at: 2026-08-17T01:30:05.459547
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Native Android development across 5 production/reference codebases: Google's architecture-samples and Now in Android, Mozilla Firefox Android, Signal, and Wikipedia. Covers Kotlin/Compose UI, MVVM with Flow, Gradle build architecture (flavors, convention plugins, version catalogs), Room/DataStore persistence, WorkManager sync, testing strategy, and Play Store release automation.

## Patterns Found (ranked by frequency)

**1. Coroutines + Flow for async (5/5)** — No RxJava anywhere. ViewModels expose `uiState: Flow<UiState>`; network layers use `suspend` functions.
```kotlin
val uiState = statisticsViewModel.uiState.first()  // arch-samples
suspend fun getDevices(): RequestResult<List<Device>, Nothing>  // Signal
```

**2. Product flavors for distribution/data variants (5/5)** — arch-samples: `mock`/`prod`; NIA: `demo`/`prod`; Wikipedia: `alpha/beta/prod/fdroid/custom/dev`; Signal: source sets per channel (`nightly`, `staging`, `canary`, `perf`, `website`); Firefox: debug URL via static flag instead.

**3. Version catalog `gradle/libs.versions.toml` (3/5)** — arch-samples, NIA, Wikipedia. Firefox uses per-product Gradle dependency plugins (predates catalogs); Signal uses build-logic included builds.

**4. KSP over KAPT (4/5)** — arch-samples, NIA, Signal, Wikipedia. Faster incremental annotation processing for Room/Hilt.

**5. Fake implementations over mocks for repositories (2/5, Google repos)**
```kotlin
tasksRepository = FakeTaskRepository()
tasksRepository.addTasks(task1, task2)  // real in-memory impl, works with Flow
```
NIA formalizes this into dedicated modules: `core/data-test`, `core/datastore-test`. Firefox contrastingly uses Mockito heavily (`doReturn`, `doThrow`, `verify`).

**6. Result wrapper types instead of exceptions (2/5)** — Firefox: `PocketResponse.Success/Failure` sealed class; Signal: `NetworkResult<T>` and `RequestResult<T, E>` (with `Nothing` for no-error paths).

**7. Type-safe navigation, three variants:**
- NIA: `@Serializable object ForYouNavKey : NavKey` (androidx.navigation3)
- Signal: `@Parcelize sealed interface AppSettingsRoute : Parcelable` with nested per-feature sealed interfaces + `data object Empty` sentinel for two-pane layouts; navigation via `ViewModel` router emitting `MutableSharedFlow<Route>`
- arch-samples: Navigation Compose, single-activity

**8. Convention plugins / build-logic included builds (2/5)** — NIA (`nowinandroid.android.feature.api`), Signal (`build-logic/plugins`, independently testable). Cost noted: indirection for new contributors.

**9. Room with schema export for migrations (3/5)** — NIA, Wikipedia (`app/schemas/`), arch-samples.

**10. Hilt DI (2/5)** — arch-samples, NIA. Firefox uses manual constructor injection with companion `newInstance()` factories; Signal not observed.

**11. Custom lint rules (2/5)** — NIA: `DesignSystemDetector` (error-level, bans raw Material → requires `NiaButton`/`NiaTheme`), `TestMethodNameDetector`. Signal: `fast-lint` module used in CI instead of full lint.

**12. Spotless + copyright headers (2/5)** — arch-samples, NIA. Firefox/Wikipedia use ktlint + detekt.

## How Problems Are Solved

**PROBLEM: Testing loading states with coroutines** (arch-samples)
```kotlin
Dispatchers.setMain(StandardTestDispatcher())  // prevent eager execution
val job = launch { viewModel.uiState.collect { isLoading = it.isLoading } }
assertThat(isLoading).isTrue()
advanceUntilIdle()
assertThat(isLoading).isFalse()
job.cancel()
```
Plus `MainCoroutineRule` JUnit rule replacing `Dispatchers.Main`.

**PROBLEM: Sharing test utilities between unit + instrumented tests** — arch-samples: `shared-test/` module; Signal: `testShared/` source set; NIA: `core/testing` + per-layer test modules.

**PROBLEM: Robust JSON parsing** (Firefox) — drop invalid entries per-field rather than failing whole response; every required field has a `WHEN missing X THEN entry dropped` test. Wikipedia: raw JSON fixtures in `test/res/raw/` (named `onthisday_MM_DD.json`) fed to deserializers instead of MockWebServer.

**PROBLEM: Modular compilation scope** (NIA) — feature `api`/`impl` split; `app` depends only on `api` (NavKey + contracts), `impl` wired via Hilt. Changing impl internals doesn't recompile app/siblings.

**PROBLEM: Enforcing library boundaries** (Firefox) — reflection-based visibility tests: `assertClassVisibility(SpocsEndpoint::class, KVisibility.INTERNAL)`.

**PROBLEM: Background sync** — NIA: dedicated `sync/work` WorkManager module + `sync/sync-test`. Only explicit WorkManager usage across the 5 repos.

**PROBLEM: Resource leaks in networking** (Firefox) — tests explicitly assert `Response.close()` via `assertResponseIsClosed()`.

**PROBLEM: Dependency integrity** — NIA: `dependencyGuard` plugin with checked-in classpath snapshot; Signal: `gradle/verification-metadata.xml` checksums + custom verification plugin.

**PROBLEM: CI test memory** (Signal) — `maxParallelForks = (cpus/4).coerceAtLeast(1)`, `maxHeapSize = "2g"`, `mustRunAfter` ordering so library tests run after heavy app tests.

## Architecture Decisions Seen

| Decision | Choices observed | Tradeoffs |
|---|---|---|
| Modularization | NIA: full feature+layer split; Signal: `app/lib/feature/core/demo` groups; Wikipedia: mostly single `app` module | Build speed & encapsulation vs. contributor complexity |
| Preferences | NIA: Proto DataStore (typed, versioned) | vs SharedPreferences: needs proto schema + consumer proguard rules |
| JSON | Wikipedia: kotlinx.serialization; Firefox: raw `org.json` (no Retrofit/Moshi); Signal: Wire protobuf + Jackson | Compile-time vs reflection; R8 compatibility |
| Networking | Firefox: `concept.fetch.Client` abstraction; Signal: REST tunneled over WebSocket | Decoupling from HTTP lib / unified connectivity |
| Proguard organization | Signal: one `.pro` file per third-party lib; Wikipedia: separate `test-proguard-rules.pro`; arch-samples: `proguardTest-rules.pro` | Granular rules vs monolith |
| Assertions | arch-samples mixes Truth (ViewModel tests) + Hamcrest (utils) — historical | |
| Release perf | NIA & Signal: baseline profiles + Macrobenchmark modules; Signal adds microbenchmarks with minified builds | |

## Testing Approaches
- **Three layers everywhere**: JVM unit (`test/`), instrumented (`androidTest/`), shared utilities module/source set
- **Test naming**: NIA lint-enforces `given_when_then`; Firefox uses backtick BDD strings `` `GIVEN x WHEN y THEN z` ``
- **Screenshot testing**: NIA (Roborazzi + `core/screenshot-testing`), Signal (`screenshotTest` source sets, CI-only validation task)
- **Negative interaction testing** (Firefox): `doThrow(AssertionError())` on collaborator to prove it's never called
- **Mockito inline mock-maker** (arch-samples) to mock final Kotlin classes
- **Demo apps per library** (Signal `demo/`) for isolated manual testing
- **Lint rule tests** (NIA): `TestLintTask` DSL; test code generated from the rule's own `METHOD_NAMES` map — zero drift

## Deployment & Production
- **Play Store automation**: Wikipedia — Fastlane + Python scripts (`bump-version-code.py`, `make-release.py`); Firefox — TaskCluster pipeline (build→sign→lint→test→push-bundle); NIA — Kokoro CI + `prodRelease-badging.txt` regression checks
- **Crash/perf monitoring**: NIA — Firebase Crashlytics + Performance (prod flavor only); Firefox — Sentry + Glean telemetry; Wikipedia — Firebase (excluded in fdroid flavor)
- **GMS-free builds**: Wikipedia fdroid flavor with stub implementations; NIA demo flavor excludes Firebase
- **Reproducible builds** (Signal): Dockerfile + `apkdiff.py` verifying Play Store APK matches source
- **Per-flavor launcher icons** (Wikipedia) for on-device variant identification
- **Feature flags/experiments**: Firefox — Nimbus FML files per feature area

## Open Questions (for reviewer)
1. **Fakes vs Mockito**: Google repos advocate fakes for Flow-based repos; Firefox uses Mockito extensively. Pick a default?
2. **Navigation**: navigation3 `NavKey` (experimental, NIA) vs Parcelable sealed routes + SharedFlow router (Signal) vs Navigation Compose string-free (arch-samples). Signal's SharedFlow router drops events if no collector — acceptable?
3. **Modularization threshold**: Wikipedia ships successfully mostly single-module; NIA/Signal are heavily modularized. When to split?
4. **JSON library**: kotlinx.serialization vs raw org.json vs Wire/protobuf — standardize?
5. **Design-system enforcement via error-level lint** (NIA): adopt, or rely on review?
6. **Release tooling**: Fastlane vs custom scripts vs CI-native pipelines — which fits our infra? (Note: infra itself is out of role scope.)
7. **WorkManager**: only NIA demonstrates it despite being in role scope — thin coverage; may need supplementary sources.
