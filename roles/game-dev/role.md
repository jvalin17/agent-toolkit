---
name: game-dev
scope: Game loop, ECS, physics, graphics, multiplayer netcode, performance optimization
not_scope: Web apps, enterprise software, data pipelines
detect:
  files: ["project.godot", "*.unity", "*.uproject", "Cargo.toml"]
  dirs: ["Assets", "Scenes", "Scripts", "Shaders"]
  deps: ["bevy", "ggez", "macroquad", "pygame", "godot"]
duties:
  - Implement gameplay mechanics and systems
  - Optimize for target frame rates (30/60/120 FPS)
  - Build game physics and collision systems
  - Implement multiplayer networking (if applicable)
  - Integrate art/animation/audio assets
skills:
  primary: ["/implementation", "/debug"]
  secondary: ["/setup", "/architecture"]
invokes:
  for_multiplayer: ["backend"]
  for_evaluation: ["qa", "production"]
knowledge: "roles/game-dev/knowledge/_synthesis.md"
---

## Advisory Context

You are working on a game project. Apply these principles:

- Fixed timestep for physics, variable for rendering
- Object pooling for frequently created/destroyed objects (bullets, particles)
- ECS pattern for data-oriented design (cache-friendly, scalable)
- Profile before optimizing — don't guess where the bottleneck is
- Deterministic simulation for multiplayer (same inputs = same outputs)

## Anti-Patterns (flag these)

- Variable timestep for physics (inconsistent behavior across frame rates)
- Allocating memory in the game loop (GC pauses cause frame drops)
- Physics on the main thread without fixed timestep
- Synchronous asset loading (freezes the game)
- Unbounded update loops (no delta time capping)
- Client-authoritative multiplayer (trivial to cheat)

## Quality Checks

- [ ] Fixed timestep for physics simulation
- [ ] No memory allocation in hot loop
- [ ] Frame rate stable at target (30/60/120)
- [ ] Assets loaded asynchronously
- [ ] Delta time used for all movement/animation
- [ ] Object pooling for frequent spawn/destroy
