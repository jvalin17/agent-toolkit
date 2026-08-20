---
role: game-dev
sources: 5
synthesized_at: 2026-08-17T02:37:18.067786
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
Knowledge synthesized from 4 game engines/frameworks (Bevy, Godot, LÖVE2D, Phaser 4) plus 1 curated index (awesome-open-source-games — contains no code, useful only as a discovery pointer). Covers game loop design, entity/component architectures, physics integration, multi-backend rendering, threading, netcode foundations, and performance patterns.

## Patterns Found (ranked by frequency across repos)

**1. Deferred Mutation / Command Queue** — 4/4 engines
- Bevy: `Commands` queues spawn/despawn/insert, applied at sync points — avoids borrow conflicts during parallel system execution
- Godot: `CommandQueueMT` (render thread bridge) + `MessageQueue` (`call_deferred()`, processed end of frame)
- Phaser: `DynamicTextureCommands.js` — drawing ops recorded for deferred execution
- LÖVE: event push/poll queue decouples OS event timing from game tick

**2. Handle/ID Indirection instead of raw pointers** — 3/4
- Bevy: `Handle<T>` for assets; data lives in `Assets<T>` resource
- Godot: `RID` (typed uint64) + `RID_Owner<T>` pools — servers own data, nodes hold handles; prevents dangling pointers across threads
- LÖVE: reference-counted `Object` base class (weaker form)

**3. Plugin/Module Architecture** — 4/4
- Bevy: `Plugin`/`PluginGroup` on `App`; every subsystem optional via feature flags
- Phaser: `PluginManager` + `InjectionMap.js` mapping plugins to scene properties (`this.physics`, `this.tweens`)
- LÖVE: module-per-system under `src/modules/` with registration
- Godot: server singletons registered at startup; GDExtension for external plugins

**4. Observer/Event System** — 4/4
- Bevy: `Observer` components + component lifecycle hooks (fire immediately on structural change), separate from scheduled systems
- Godot: signal/slot on core `Object` class with runtime reflection (`ClassDB`)
- Phaser: EventEmitter3 wrapping; SCREAMING_SNAKE_CASE event constants per system (`STEP`, `PRE_RENDER`, `POST_RENDER`)
- LÖVE: `love.event.push()` / `poll()` iterator, up to 6 args per event

**5. ECS spectrum** — all 4 take different positions:
- Bevy: pure archetype ECS; systems are functions with typed params: `fn movement(mut q: Query<(&mut Transform, &Velocity)>, time: Res<Time>)`
- Godot: OOP node tree; ECS-adjacent only in servers (RID = component store)
- Phaser: prototype mixin composition (`src/gameobjects/components/`) — explicitly rejected true ECS as unjustified for typical 2D entity counts
- LÖVE: no entity model at all — left to Lua game code

**6. Renderer Strategy / Multi-Backend** — 4/4
- Godot: `RenderingDevice` (portable API) → `RenderingDeviceDriver` (Vulkan/D3D12/Metal/GLES3)
- Bevy: wgpu abstraction (Metal/Vulkan/DX12/WebGPU) + render graph
- LÖVE: OpenGL + Vulkan, shader unification via glslang → SPIRV-Cross transpilation
- Phaser: WebGL-first with Canvas fallback selected at init via capability detection

**7. Scripting/API boundary** — Godot (GDExtension stable C ABI), LÖVE (Lua-hosted logic on C++ core), Phaser (JS with JSDoc→.d.ts generation), Bevy (Rust-native, reflection via `bevy_reflect`)

## How Problems Are Solved

**PROBLEM: Fixed timestep vs frame-rate rendering**
- Bevy: separate `FixedUpdate` (physics) and `Update` (render-rate) schedules
- Godot: `_physics_process(delta)` fixed / `_process(delta)` variable; `InterpolatedProperty<T>` stores prev+current state, lerps at render time via `physics_interpolation_fraction` — solves fixed-timestep visual stutter
- LÖVE: deliberately not enforced — exposes `dt`, developers implement their own accumulator
- Phaser: `TimeStep.js` on `requestAnimationFrame`; per-scene ordered pipeline (physics → user update → tweens → timers → cameras → render)

**PROBLEM: Render/simulation thread separation**
- Bevy: extract pattern — main world copied into isolated render world each frame; enables pipelining (render frame N-1 while simulating N)
- Godot: dedicated render thread fed via `CommandQueueMT` ring buffer; tradeoff noted: 1-frame latency for CPU/GPU overlap
- Phaser/LÖVE: single-threaded (browser/Lua constraints)

**PROBLEM: Spatial queries / broadphase**
- Godot: custom incremental BVH (`bvh_tree.h` + `.inc` files for cull/refit/pair ops), dynamic insert/remove without full rebuild
- Phaser: Arcade physics AABB broadphase; Matter.js bundled for full polygon/constraint physics
- LÖVE: bundled Box2D
- Bevy: no built-in physics — integration point is `FixedUpdate` schedule + transform hierarchy; external crates via plugin pattern

**PROBLEM: Netcode foundations**
- Godot: `Variant` as universal wire format, delta encoding in core IO, `MultiplayerAPI` RPC dispatch, input event codec for remote players
- LÖVE: bundled ENet (UDP) + LuaSocket (TCP), exposed to Lua
- Bevy: no built-in netcode; determinism support (per-column change ticks), scene serialization as replication substrate, external crates (lightyear)
- Phaser: none (client-only)

**PROBLEM: Performance at scale**
- Bevy: automatic parallel system execution when queries don't conflict; change detection to skip unchanged data; stress tests (`many_cubes`, `bevymark`); schedule randomization to detect ordering ambiguities
- Godot: `PagedAllocator<T>` for hot-path allocations, COW data, `LocalVector<T>` (no COW overhead), lock-free `SafeList`, spinlocks
- Phaser: GPU tilemap layer (tile logic in shaders, bypasses CPU iteration), GPU particle emitters

**PROBLEM: Asset pipeline**
- Bevy: async `AssetServer`, hot-reloading, processing pipeline, KTX2 GPU-native textures
- Godot: `.pck` virtual filesystem with encryption + delta patch support
- LÖVE: PhysFS mounts `.love` (zip) archives transparently
- Phaser: global `TextureManager` (shared across scenes — chosen over per-scene isolation for VRAM dedup); multi-format atlas parsers

## Architecture Decisions Seen

| Decision | Choices observed | Tradeoff |
|---|---|---|
| Entity model | Pure ECS (Bevy) vs node tree (Godot) vs mixins (Phaser) | Cache locality & parallelism vs ergonomics/scriptability |
| Physics | External-by-design (Bevy) vs pluggable servers (Godot) vs bundled Box2D/Matter (LÖVE, Phaser) | Flexibility vs zero-setup friction |
| Dependencies | Vendor everything (LÖVE, Phaser bundles Matter.js) vs workspace crates (Bevy) | Reproducible builds vs update burden |
| Error handling | No exceptions anywhere: Rust `Result` + boxed errors (Bevy), macro return-codes `ERR_FAIL_COND_V` (Godot), Lua error propagation (LÖVE), errors propagate (Phaser) | Consistent industry pattern: exceptions avoided in game loops |
| Extension ABI | Stable C ABI (Godot GDExtension) vs Rust plugin trait (Bevy) | ABI stability vs binding verbosity |
| Headless support | Feature-flag profiles + no_std (Bevy), dedicated server export (Godot) | Both support server builds explicitly |

## Testing Approaches
- **Bevy**: integration tests (`tests/`), compile-fail UI tests for ECS invariants, ambiguity detection tests, documented user-facing patterns (`how_to_test_systems.rs`), criterion benchmarks, stress tests as perf regression tools
- **LÖVE**: test suite runs *as a game* (`love testing`); custom assertions (`test:assertEquals`); pixel-diff render testing (actual/expected/difference dirs); hardware-dependent tests check API existence only
- **Phaser**: Vitest + jsdom, tests mirror `src/` 1:1; WebGL/game-loop testing limited by jsdom; no E2E
- **Godot**: separate `tests/` dir; runtime debugger infrastructure (remote debugger over TCP, profiler hooks) substitutes for some test tooling

## Deployment & Production
- **Godot**: per-platform export plugins, `.pck` packing (encrypted, delta-patchable), dedicated-server export, remote debugging over TCP
- **LÖVE**: `.love` zip + engine binary; NSIS/deb/Xcode per platform; no telemetry
- **Phaser**: npm + CDN (jsDelivr/cdnjs); CJS/ESM/minified bundles; client-side only
- **Bevy**: library crates; WASM tooling; feature profiles gate headless/no_std builds
- **Common**: none ship crash reporting/telemetry in core

## Open Questions (for reviewer)
1. **Entity architecture**: pure ECS (Bevy) vs mixin/OOP (Phaser/Godot) — Phaser explicitly argues ECS overhead is unjustified below ~10k entities. Which default for this role's guidance?
2. **Fixed timestep**: engine-enforced (Bevy/Godot) vs developer-implemented (LÖVE). Godot's `InterpolatedProperty` interpolation pattern is the most complete stutter solution — adopt as recommended pattern?
3. **Physics coupling**: bundle (LÖVE/Phaser) vs plugin integration point (Bevy/Godot)?
4. **Netcode**: only Godot ships a full stack (Variant serialization + delta encoding + RPC). Bevy delegates to ecosystem. Is Godot's approach the reference, or is layered-external (ENet-style) preferred?
5. **awesome-open-source-games** source contributed nothing implementable — drop from knowledge base, or keep as discovery index?
6. **Testing gap**: no source has a robust story for automated game-loop/renderer testing (jsdom limits, pixel-diff flakiness). Flag as known unsolved area?
