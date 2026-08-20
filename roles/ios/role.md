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
