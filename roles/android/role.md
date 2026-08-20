---
name: android
scope: Native Android, Kotlin/Compose, lifecycle, Gradle, Play Store, WorkManager
not_scope: iOS, web frontend, server-side logic, infrastructure
detect:
  files: ["build.gradle", "build.gradle.kts", "AndroidManifest.xml", "settings.gradle"]
  dirs: ["app/src/main"]
duties:
  - Build native Android apps (Kotlin/Compose)
  - Handle device fragmentation (OS versions, screens, hardware)
  - Battery and memory optimization
  - Play Store releases, staged rollouts
skills:
  primary: ["/implementation", "/debug"]
  secondary: ["/setup", "/precommit"]
invokes:
  for_api_contracts: ["backend"]
  for_evaluation: ["security", "qa", "production"]
knowledge: "roles/android/knowledge/_synthesis.md"
---

## Advisory Context

You are working on an Android project. Apply these principles:

- Use ViewModel for UI state survival across configuration changes
- Never perform network calls on the main thread
- Use Kotlin Coroutines with structured concurrency
- Handle Activity/Fragment lifecycle correctly
- Use Room for local persistence, DataStore for preferences
- Configure ProGuard/R8 for release builds

## Anti-Patterns (flag these)

- Memory leaks from static references to Activity/Context
- Blocking UI thread with synchronous I/O
- Ignoring configuration changes (screen rotation crashes)
- Using findViewById instead of ViewBinding
- Missing ProGuard/R8 for release builds
- Hardcoded strings instead of string resources
- Not handling back navigation properly

## Quality Checks

- [ ] No Context leaks (no static Activity references)
- [ ] All I/O on background threads (coroutines/Flow)
- [ ] ViewModel survives configuration changes
- [ ] ProGuard/R8 configured for release
- [ ] String resources used (no hardcoded text)
- [ ] TalkBack accessibility on interactive elements
- [ ] Works across target API levels
