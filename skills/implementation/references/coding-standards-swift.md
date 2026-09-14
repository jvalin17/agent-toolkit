# Swift Coding Standards

> Our synthesis of Swift API Design Guidelines and community best practices. Follow official guidelines for the authoritative source.
> Last verified: 2026-09-14

## Sources
- [Swift API Design Guidelines](https://www.swift.org/documentation/api-design-guidelines/)
- [Google Swift Style Guide](https://google.github.io/swift/)
- [Ray Wenderlich / Kodeco Swift Style Guide](https://github.com/kodecocodes/swift-style-guide)

---

## Imports
```swift
// GOOD: minimal imports, grouped Apple then third-party
import Foundation
import UIKit

// BAD: duplicates (UIKit already includes Foundation), unused imports
import Foundation
import UIKit
import Foundation  // duplicate
```

**Rules:**
- Prefer `Foundation` for non-UI code; add `UIKit`/`SwiftUI` only where needed.
- Alphabetize within groups. Blank line between Apple and third-party.
- Never import a framework just to silence a warning. Find the real dependency.

## Naming
```swift
// GOOD
struct UserProfile { }
var isAuthenticated = false
func fetchUser(withID id: String) async throws -> User
let users: [User]          // not userArray
image.crop(to: rect)       // not image.cropImage(to:)

// BAD: vague, abbreviated, or redundant
var data: Any              // data what?
func process()             // process what?
let userObject = User()    // "Object" is noise
```

**Rules:**
- Types and protocols: `PascalCase`. Everything else: `camelCase`.
- Boolean properties read as assertions: `isLoading`, `hasUnsavedChanges`, `canSubmit`.
- Parameter labels clarify call-site meaning: `move(from:to:)`, not `move(_:_:)`.
- Omit needless words; don't abbreviate unless universal (`URL`, `ID`).

## Optionals
```swift
// GOOD: guard let for early exit, if let for scoped use, ?? for defaults
func displayName(for user: User?) -> String {
    guard let user = user else { return "Guest" }
    return user.name
}
let title = response.title ?? "Untitled"

// BAD: force unwrap — crashes at runtime on nil
let name = user!.name
let url = URL(string: rawURL)!
```

**Rules:**
- Never force-unwrap (`!`) in production code. Use `guard let`, `if let`, or `??`.
- `guard let` for early-exit conditions at the top of a function.
- Use `compactMap` instead of `map` + force-unwrap.
- IBOutlets are the one accepted exception (bad wiring crashes regardless).

## Protocols
```swift
// GOOD: behavior via protocols + extensions, Codable for serialization
protocol Displayable {
    var displayName: String { get }
}
extension Displayable {
    func formatted() -> String { "[\(displayName)]" }
}
struct Article: Codable { let id: UUID; let title: String }

// BAD: base class to share behavior
class BaseViewController: UIViewController {
    func showError(_ msg: String) { ... }  // use a protocol extension instead
}
```

**Rules:**
- Prefer protocol composition over class inheritance for shared behavior.
- Use `Codable` for all data models that cross a boundary.
- Name protocols after capabilities: `Loadable`, `Persistable`, `Authenticating`.
- Add default implementations via extensions, not base classes.

## Memory Management
```swift
// GOOD: weak self prevents retain cycles in escaping closures
networkManager.fetch(request) { [weak self] result in
    guard let self = self else { return }
    self.handleResult(result)
}

// BAD: strong capture — cycle when viewModel is owned by self
viewModel.onUpdate = { self.tableView.reloadData() }
```

**Rules:**
- Always use `[weak self]` in escaping closures stored on objects you own.
- Prefer `[weak self]` over `[unowned self]` unless lifetimes are provably equal.
- Use Instruments → Leaks to verify before shipping.
- Add `deinit { print("deallocated") }` during development to confirm deallocation.

## Concurrency
```swift
// GOOD: async/await + MainActor + actor for shared state
func loadFeed() async throws -> [Post] {
    let data = try await apiClient.get("/feed")
    return try JSONDecoder().decode([Post].self, from: data)
}
@MainActor func updateUI(with posts: [Post]) { tableView.reloadData() }

actor Cache {
    private var store: [String: Data] = [:]
    func value(for key: String) -> Data? { store[key] }
}

// BAD: raw GCD for new code
DispatchQueue.global().async {
    let result = self.compute()
    DispatchQueue.main.async { self.label.text = result }
}
```

**Rules:**
- Use `async/await` for all new asynchronous code. Avoid raw `DispatchQueue` / callbacks.
- Mark UI-touching methods `@MainActor`; use `await MainActor.run { }` for inline updates.
- Use `actor` to protect shared mutable state across concurrent tasks.
- Use `async let` and `TaskGroup` for structured parallel work.

## Error Handling
```swift
// GOOD: typed errors + do-catch with specific cases
enum AuthError: Error { case invalidCredentials, tokenExpired, serverError(Int) }

do {
    let user = try await authService.signIn(email: email, password: password)
    navigateToHome(user: user)
} catch AuthError.invalidCredentials {
    showAlert("Check your email and password.")
} catch { showAlert("Something went wrong: \(error.localizedDescription)") }

// BAD: try? silently discards the failure reason
let user = try? authService.signIn(...)
```

**Rules:**
- Define custom `Error` enums per domain. Never throw `NSError` from new Swift code.
- Catch specific cases first, then a general `catch` as fallback.
- `try?` only when failure is truly irrelevant (e.g., optional cache hit).
- Use `Result<Success, Failure>` for synchronous APIs that can fail.

## Common Anti-Patterns
```swift
// BAD: force unwrap
let url = URL(string: str)!

// BAD: Massive View Controller — business logic inside UIViewController
class FeedViewController: UIViewController {
    func loadData() { /* networking + parsing + state management inline */ }
}

// BAD: stringly-typed identifiers
tableView.register(UINib(nibName: "UserCell", bundle: nil), forCellReuseIdentifier: "UserCell")
// GOOD:
extension UserCell { static let reuseID = String(describing: UserCell.self) }

// BAD: strong delegate causes retain cycle
class ViewModel { var delegate: SomeViewController }
// GOOD:
weak var delegate: SomeViewControllerDelegate?
```

**Rules:**
- No force unwrap in production. Treat compiler warnings as errors (`-warnings-as-errors`).
- Keep `UIViewController` thin: delegate networking and state to ViewModels or services.
- Use typed constants (enums, static lets) for reuse IDs, notification names, segue IDs.
- Delegate properties must always be `weak` to avoid retain cycles.
