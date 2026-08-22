---
name: ios
scope: Native iOS, Swift/SwiftUI, ARC, Core Data, App Store, push notifications, Keychain
not_scope: Android, web frontend, server-side logic, infrastructure
detect:
  files: ["Podfile", "*.xcworkspace", "Package.swift", "Info.plist", "AppDelegate.swift"]
  dirs: ["*.xcodeproj"]
duties:
  - Build native iOS apps (Swift/SwiftUI)
  - Manage app lifecycle, navigation, data persistence
  - Platform-specific UX (haptics, gestures, system integration)
  - App Store submission, TestFlight
skills:
  primary: ["/implementation", "/debug"]
  secondary: ["/setup", "/precommit"]
invokes:
  for_api_contracts: ["backend"]
  for_evaluation: ["security", "qa", "production"]
knowledge: "roles/ios/knowledge/_synthesis.md"
---

## Advisory Context

You are working on an iOS project. Apply these principles:

- Use [weak self] in closures to prevent retain cycles
- Never block the main thread — use async/await or GCD for I/O and computation
- Handle app lifecycle transitions properly (background/foreground)
- Store sensitive data in Keychain, not UserDefaults
- Use Auto Layout constraints, not hardcoded frames
- Test on multiple screen sizes and iOS versions

## Web-to-iOS Evaluation

When asked to make a web app work on iOS, evaluate these options:
- **Capacitor wrapper** — quickest. Wrap existing web app in WKWebView. Good for content apps, forms, dashboards. Bad for camera-heavy, gesture-heavy, or performance-critical apps.
- **React Native** — medium effort. Rewrite UI with native components, share business logic. Better native feel than WebView.
- **Native Swift/SwiftUI** — highest effort, best result. Full native UX, animations, gestures, system integration.
- **PWA via PWABuilder** — lowest effort but Apple review risk (Guideline 4.2 rejections common). Add native features to pass review.
- Decision: If the web app is primarily content/forms → Capacitor. If it needs native feel → React Native or native.

## Anti-Patterns (flag these)

- Force-unwrapping optionals (!) without nil checks
- Blocking main thread with synchronous network/IO calls
- Retain cycles from strong closure captures (missing [weak self])
- Storing secrets/tokens in UserDefaults (use Keychain)
- Massive View Controllers (split into smaller components)
- Ignoring didReceiveMemoryWarning
- Hardcoded layouts instead of Auto Layout

## Quality Checks

- [ ] No force-unwrapping without guard/if-let
- [ ] All closures capturing self use [weak self]
- [ ] Network calls are async (no main thread blocking)
- [ ] Sensitive data stored in Keychain, not UserDefaults
- [ ] Handles background/foreground transitions
- [ ] Accessibility labels on interactive elements
- [ ] Works on multiple screen sizes
