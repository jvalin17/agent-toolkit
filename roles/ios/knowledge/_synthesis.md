---
role: ios
sources: 5
synthesized_at: 2026-08-17T01:22:36.418836
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Native iOS engineering across Swift/SwiftUI, ARC, Core Data, App Store distribution, push notifications, and Keychain. Synthesized from 5 repos: Alamofire (networking library), Firefox iOS (browser app), TCA (architecture framework), Signal iOS (encrypted messenger), Wikipedia iOS (content app).

## Patterns Found (ranked by frequency across repos)

**1. Coordinator Pattern for Navigation** — Firefox (ADR 0002, `Client/Coordinators/`), Signal (`RegistrationCoordinator.swift`, `ProvisioningCoordinatorImpl.swift`). VCs don't push/present; Signal drives VCs via `RegistrationStep` enum values from coordinator.

**2. Delegate Pattern (weak, AnyObject-constrained)** — Alamofire (`SessionDelegate`, `RequestDelegate`), Signal (merge observers), Wikipedia:
```swift
protocol ShortDescriptionControllerDelegate: AnyObject {
    func currentDescription(completion: @escaping (String?) -> Void)
}
private weak var delegate: ShortDescriptionControllerDelegate?
```

**3. Modular Swift Package Architecture** — Firefox (`BrowserKit` with per-concern kits: `TabDataStore`, `ToolbarKit`, `MenuKit`, each independently testable), Wikipedia (`WMFData`, `WMFComponents`, `WMFLocalizations`), TCA/Alamofire (SPM as primary distribution).

**4. Dependency Injection — three variants:**
- Default-parameter init injection (Wikipedia): `init(wikitextFetcher: WikitextFetcher = WikitextFetcher(), ...)` — production uses defaults, tests inject mocks
- Property-wrapper/global container (TCA): `@Dependency(\.mainQueue) var mainQueue`, overridden per-test via `withDependencies { }`
- Service locator/environment (Signal): `SSKEnvironment`, `DependenciesBridge`, `AppEnvironment`

**5. Protocol-Oriented Strategy Pattern** — Alamofire (pluggable `ResponseSerializer`, `ParameterEncoder`, `ServerTrustEvaluating`), Wikipedia (`ArticleDescriptionControlling` with two conformers — Wikidata API vs. wikitext regex editing — shared validation in protocol extension defaults), Signal (Protocol + Shims for test injection).

**6. Unidirectional Data Flow / Redux** — TCA (reducer pattern, value-type state, effects as values), Firefox (deliberate MVVM→Redux migration, ADRs 0003–0005, 0011–0013, `@Copy` macro for reducer boilerplate).

**7. Extension-file naming `TypeName+FunctionalArea.swift`** — Signal (`ConversationViewController+Banners.swift`), Alamofire (test extensions), plus `Impl` suffix for concrete conformances (Signal: `RegistrationCoordinatorImpl`; also `Mock` prefix for doubles in Signal/Firefox).

**8. Job Queue / persisted background work** — Signal (`MessageSenderJobQueue`, `JobQueueRunner`, persisted `JobRecords/` surviving termination), Wikipedia (NSOperation-based `RemoteNotificationsOperationsController`).

**9. Builder/Fluent chaining** — Alamofire (every request method returns `Self`), Signal (`GroupSendFullTokenBuilder`).

**10. Custom concurrency primitives** — Alamofire (`Protected<T>` reader-writer wrapper), Signal (rich toolkit: `SerialTaskQueue`, `CancellableContinuation`, `CooperativeTimeout`/`UncooperativeTimeout`, `TSMutex`).

## How Problems Are Solved

**PUSH NOTIFICATIONS** (3 approaches):
- Signal: `UNNotificationServiceExtension` (`SignalNSE/`) decrypts E2E-encrypted push payloads; `PushRegistrationManager` for APNs tokens; `SyncPushTokensJob` job-queue-backed token sync with retry; `NSECallMessageHandler` for VoIP pushes
- Firefox: Rust-backed Autopush client (`Push/Autopush.swift`) + NSE for decryption/display
- Wikipedia: NSE with shared `NotificationServiceHelper.swift` between extension and main app; NSOperation subsystem for remote notification fetch

**KEYCHAIN / SECURE STORAGE:**
- Signal: `AccountKeyStore` abstracts Keychain; crypto material (PreKey/Session stores) in DB encrypted with Keychain-protected key; `LocalDeviceAuthentication` gates ops behind Face ID; `NoAutofillSecureEntryTextField` blocks autofill on sensitive fields
- Firefox: `RustKeychain.swift` wrapper + `MockRustKeychain.swift` test double; `CredentialProvider/` (ASCredentialProvider) for password autofill integration

**PERSISTENCE** (3 approaches — no repo uses Core Data + NSFetchedResultsController conventionally):
- Wikipedia: Core Data with versioned models (`Wikipedia.xcdatamodeld` — 8 versions, `.xcmappingmodel` migrations); events staged in Core Data before network send
- Signal: custom SDS codegen (Python scripts generate ORM code over GRDB/SQLite) — explicit rejection of Core Data threading pitfalls, at cost of no automatic migrations
- Firefox: Rust components (Places, Logins) + dedicated `TabDataStore` kit; lazy tab screenshot restoration (ADR 0008)

**MEMORY / ARC:**
- Signal: explicit bounded caches (`CVMediaCache`, `StickerViewCache`)
- Firefox: offload background WKWebViews on memory warning (ADR 0010)
- Alamofire: `LeaksTests.swift` for explicit ARC leak verification; `stored()` test helper to prevent premature dealloc
- TCA: `MemoryManagementTests` for retain-cycle validation
- Wikipedia: dedicated `missingSelf` error case for `[weak self]` nil checks instead of force-unwrap

**FEATURE FLAGS:**
- Firefox: Nimbus/Experimenter YAML per feature, runtime remote config, AI kill-switch flags
- Signal: five build-time flag sets generated by Python into `BuildFlags+Generated.swift` + runtime `RemoteConfigManager` as second layer
- TCA: flags flow through `@Dependency` system, no config files

**AUTH / CREDENTIAL REFRESH:**
- Alamofire: generic `AuthenticationInterceptor<A: Authenticator>` handles refresh + retry; `RequestInterceptor` = `RequestAdapter` + `RequestRetrier` chain
- Firefox: `JWTKit` custom kit for FxA token verification; `AppAttestKit` for DCAppAttestService

**ASYNC EFFECTS / SIDE EFFECTS:**
- TCA: synchronous reducers; effects as values via `.run { send in ... }` with typed enum cancel IDs (`enum CancelID { case sleep }`); escaped-`send` detection emits runtime warnings
- Wikipedia: closure + `Result` callbacks, `DispatchGroup` fan-out, explicit `DispatchQueue.main.async` at completion boundaries (not yet on async/await)
- Alamofire: triple API surface — closures, Combine, async/await in parallel

## Architecture Decisions Seen

| Decision | Choices observed | Tradeoffs noted |
|---|---|---|
| App extension targets | Signal (NSE, Share, shared `SignalServiceKit`/`SignalUI` frameworks), Firefox (NSE, ShareTo, CredentialProvider, WidgetKit), Wikipedia (NSE, Widgets, Stickers) | Shared code must live in framework; extensions need duplicate env bootstrap but clean isolation; per-variant entitlements files |
| State management | Firefox chose Redux over MVVM (documented in ADRs); TCA reducer+effects; Signal manager/store separation | Redux: boilerplate (mitigated by macros); TCA sync reducers keep mutation race-free |
| Build config | xcconfig externalized from pbxproj (Signal `Config/*.xcconfig` + `User.xcconfig` local override; Firefox; Wikipedia per-env Info.plists) | — |
| Cross-platform core | Firefox & Signal share logic cross-platform (Rust components / protobuf wire format) vs. pure-Swift elsewhere | Schema-enforced consistency vs. FFI complexity |
| ADRs for decisions | Firefox maintains `adr/` directory documenting Redux, coordinators, memory, deeplinks | Notable practice worth adopting |
| Value-type state | TCA: struct state for O(1) test diffing, no shared mutation | Requires macros (`@ObservableState`) to bridge to SwiftUI observation |

## Testing Approaches

- **XCTestExpectation async pattern** (Alamofire): `expectedFulfillmentCount` to detect unexpected lifecycle events; `wait(for:enforceOrder: true)`; `@MainActor` test methods
- **Exhaustive TestStore** (TCA): every action/state change must be asserted (`await store.send(.incr) { $0 = 1 }`); unfinished effects fail tests; `XCTExpectFailure` to test the test infrastructure itself; `DispatchQueue.test` (CombineSchedulers) for deterministic time
- **Mocks as separate package target** (Wikipedia `WMFDataMocks`, Firefox `TestKit`) — keeps mocks out of production builds
- **Snapshot/visual regression** (Wikipedia `ReferenceImages_64/`, Firefox fastlane SnapshotHelper)
- **Robot pattern for UI tests** (Wikipedia: per-screen robot classes, `ROBOTS.md`)
- **xctestplans per platform/tier** (Alamofire per-OS, Firefox Smoke/Full/Unit, Wikipedia per-package)
- **Fixtures**: canned JSON responses (Wikipedia, Alamofire), real certificates for pinning tests (Alamofire), pre-built SQLite DBs + archived tab states (Firefox)
- **Base test classes** (Alamofire `BaseTestCase`, TCA `BaseTCATestCase`) for shared setup

## Deployment & Production

- **CI/CD**: Bitrise + Taskcluster + Fastlane (Firefox); CircleCI + Xcode Cloud `ci_scripts/` (Wikipedia); Danger + SwiftLint PR gating (Firefox); SwiftLint + ClangFormat pre-commit (Wikipedia)
- **TestFlight automation**: Firefox `nightly_testflight_add_group.py`, `WhatToTest.en-US.txt` per release
- **Multi-brand/variant builds**: per-variant entitlements (Firefox/
