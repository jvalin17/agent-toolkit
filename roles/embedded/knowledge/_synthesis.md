---
role: embedded
sources: 5
synthesized_at: 2026-08-17T02:45:11.868935
---

## [DRAFT — HUMAN REVIEW REQUIRED]

## Role Summary
This role covers firmware runtimes and HALs (embassy, MicroPython), firmware code-generation systems (ESPHome), IoT protocol servers/device connectivity (ThingsBoard, Home Assistant), OTA update mechanisms, power management, and RTOS/async concurrency models. Sources span bare-metal Rust, embedded C/Python VMs, and the host/cloud side of device management — the common thread is resource-constrained device operation and device↔host protocols.

## Patterns Found (ranked by frequency across repos)

### 1. Cooperative async / event-loop concurrency (5/5 repos)
No preemptive threading in the core; everything yields cooperatively.
- **embassy**: compiler-generated async state machines, static allocation, no heap. `#[embassy_executor::task] async fn my_task() { Timer::after_millis(100).await; }`
- **MicroPython**: `extmod/asyncio/` frozen into most ports; `_thread` optional (FreeRTOS/pthreads)
- **ESPHome**: sequential `Component::loop()` calls in `Application::loop()` — no RTOS abstraction in core
- **Home Assistant**: single asyncio loop; blocking I/O forbidden and enforced at runtime (`block_async_io.py`)
- **ThingsBoard**: Netty async NIO for transports + actor model (`common/actor/`)

### 2. HAL / port abstraction layer (4/5)
Hardware-specific code isolated behind a contract; generic fallback provided.
- **MicroPython**: `mphalport.h` per port (`mp_hal_ticks_ms`, `mp_hal_delay_ms`); `extmod/machine_i2c.c` soft-I2C fallback, ports override with hardware versions
- **embassy**: per-chip HAL crates (`embassy-nrf`, `embassy-stm32`, ...) over shared `embassy-hal-internal`; type-state peripheral ownership: `let spim = Spim::new(p.SPI0, irqs, sck, miso, mosi, config);` — move semantics prevent double-use at compile time
- **ESPHome**: platform guards `#ifdef USE_ESP32` / `USE_ESP8266`; Arduino vs ESP-IDF dual backends
- **Home Assistant**: Entity/EntityPlatform hierarchy as a "driver model" (device-specific code in integrations, generic in base classes)

### 3. Runner/Control split (driver task owns hardware, user API via channel) (2/5)
- **embassy**: `cyw43/src/runner.rs` (owns SPI bus, dedicated task) + `control.rs` (user API, sends ioctls via channel); repeated in esp-hosted driver
- **ThingsBoard**: same shape at service scale — transport microservice owns the device connection, core communicates via message queue

### 4. Compile-time configuration layering (4/5)
- **MicroPython**: `mpconfigport.h` → `mpconfigboard.h` → auto-detected; flags like `MICROPY_HW_*`, `MICROPY_PY_*`
- **ESPHome**: YAML → generated `defines.h` + `sdkconfig.defaults.<chip>` overlays
- **embassy**: Cargo features per chip variant; shared `build_common.rs` across HAL build scripts
- **ThingsBoard**: YAML + env-var substitution per deployable service

### 5. ROM/flash-resident data to save RAM (3/5)
- **MicroPython**: QSTR interned strings, `MP_ROM_QSTR`/`MP_ROM_PTR` tables in flash, frozen `.mpy` bytecode modules
- **embassy**: firmware blobs via `include_bytes!` (`&'static [u8]`), static task allocation
- **ESPHome**: custom protobuf codegen (no runtime library, no reflection/descriptor pool)

### 6. Code generation over runtime flexibility (3/5)
- **ESPHome**: YAML → Python codegen → C++ firmware; custom protobuf compiler emitting only `encode()`/`calculate_size()`
- **Home Assistant**: `homeassistant/generated/` — auto-generated protocol lookup tables (zeroconf, dhcp, bluetooth, usb)
- **MicroPython**: `mpy-cross` AOT bytecode compiler; QSTR table generation

## How Problems Are Solved

### OTA firmware updates — 4 distinct approaches
- **A/B partition bootloader** (embassy-boot): write to inactive partition → mark pending → reboot → validate SHA digest → swap or revert. Platform flash drivers in `embassy-boot-{nrf,rp,stm32}`
- **Push-based custom protocol** (ESPHome `espota2.py`): UDP discovery + TCP transfer from host; ESP32 uses native dual-partition underneath
- **Dedicated bootloader / bootrom** (MicroPython): STM32 `mboot/` (USB DFU), SAMD `mboot/`, RP2 UF2 drag-and-drop, ESP32 `esp_ota_*` wrapped in Python
- **Standards-based server-side** (ThingsBoard): LwM2M Object 5 (FOTA) via Leshan; Home Assistant exposes `update` entity platform, transport integration-specific

### Power management — no shared framework anywhere
- **embassy**: executor calls WFI/WFE when idle via platform pender hook (`embassy-executor/src/pender.rs`); dedicated `low_power` modules per HAL
- **MicroPython**: per-port `machine.lightsleep()`/`deepsleep()` calling native SDK APIs — explicitly no cross-port framework
- **ESPHome**: `deep_sleep` component
- **Home Assistant**: none (Linux host); debounce helper reduces wake activity indirectly

### Interrupt handling without heap/reentrancy hazards
- **embassy**: ISR signals `Waker`, task resumes at `.await` — no polling, no semaphores
- **MicroPython**: IRQ callbacks scheduled via ring buffer into main VM context; hard IRQs must not allocate heap (`docs/reference/isr_rules.rst`, `shared/runtime/mpirq.c`)
- **embassy**: lock-free atomic ring buffer for DMA UART (producer=DMA, consumer=task, no mutex)

### Shared bus (SPI/I2C multi-device)
- **embassy**: `embassy-embedded-hal/src/shared_bus/` — mutex-wrapped bus, lock per transaction, sync + async variants
- **ESPHome**: bus components auto-loaded; `script/analyze_component_buses.py` for static analysis

### Wire protocol backward compatibility
- **ESPHome**: field numbers and message IDs pinned by tests parsing generated C++ (`test_api_proto.py`); `[deprecated=true]` fields skipped entirely in codegen; `SUPERSEDED_FIELDS` dict prevents deprecation of fields old clients need; capabilities negotiation (`DeviceCapabilitiesRequest/Response`)
- **ThingsBoard**: shared `.proto` in `common/proto/`, protobuf between transport and core

### Flash filesystems / wear leveling
- **MicroPython**: LittleFS v2 for internal flash, FatFS for SD cards, VFS layer allowing simultaneous mounts; generic SPI flash driver (`drivers/memory/spiflash.c`) with soft-SPI/QSPI fallbacks

### Networking stacks
- **embassy**: smoltcp behind `embassy-net-driver` trait; drivers for WiFi (cyw43 via PIO-offloaded SPI, esp-hosted), Ethernet, cellular PPP, TUN/TAP
- **MicroPython**: lwIP + mbedTLS; ESP-NOW; esp-hosted co-processor driver; NINA AT-style WiFi
- **ThingsBoard**: MQTT (custom Netty), CoAP (Californium, DTLS/blockwise/observe), LwM2M (Leshan), SNMP
- **Home Assistant**: discovery via mDNS/DHCP-sniffing/BLE-advertisement/USB VID-PID tables

### Device provisioning / persistent identity
- **Home Assistant**: ConfigEntry (unique_id + credentials, restart-safe) + device/entity registries — analogous to NVS/EEPROM config
- **embassy**: firmware blob vs NVRAM separation (shared firmware, board-specific `nvram_*.bin`)

## Architecture Decisions Seen

| Decision | Choice | Tradeoff noted |
|---|---|---|
| Concurrency model | Cooperative everywhere (all 5) | No preemption; blocking calls must be banned/offloaded |
| Task allocation | Static at compile time (embassy) vs GC heap (MicroPython fixed mark-sweep heap) | Determinism vs flexibility |
| Protocol runtime | Codegen-only protobuf, no runtime lib (ESPHome, embassy esp-hosted) vs full protobuf (ThingsBoard server-side) | Flash/RAM savings vs reflection features |
| Transport isolation | Separate deployable transport nodes (ThingsBoard) — protocol bugs can't crash core, independent scaling, DMZ placement | Ops complexity |
| Memory layout | Linker-script driven (embassy `memory.x`, RAM-run test variant, link-time `ASSERT`s for alignment) | — |
| Error handling | `Result<T,E>` (embassy) / `longjmp` via `mp_raise_*` (MicroPython) / `mark_failed()` + no C++ exceptions (ESPHome) / exception hierarchy, failures isolated per-integration (HA) | — |
| Logging | Feature-flag switchable `fmt.rs` per crate: defmt on-target, `log` on host (embassy, every crate); `ESP_LOG*` + compile-time verbosity (ESPHome); lazy `%s` interpolation lint-enforced (HA) | — |

## Testing Approaches
- **Host-side hardware mocking via trait/interface**: embassy TUN/TAP driver implements the net-driver trait (network stack tests without hardware); ESPHome host-platform native Linux build for integration tests; HA mocks all hardware (`unittest.mock`, explicitly no HIL)
- **HIL**: only embassy — `tests/` on real hardware, `link_ram_cortex_m.x` runs firmware from RAM for fast CI iteration
- **Compile-time correctness as tests**: embassy UI tests (assert invalid code fails to compile), type-state ownership eliminates double-use runtime tests, linker `ASSERT`s
- **Protocol invariant pinning**: ESPHome parses generated C++ text to assert wire IDs/field numbers unchanged
- **Memory regression in CI**: ESPHome ELF analysis (`analyze_memory/` — demangle, RAM strings) + PR comments with memory deltas
- **Infrastructure-in-Docker**: ThingsBoard TestContainers + TestNG black-box tests
- **Async-native tests**: HA `asyncio_mode="auto"`, snapshot testing via syrupy

## Deployment & Production
- **Flashing**: probe-rs/
