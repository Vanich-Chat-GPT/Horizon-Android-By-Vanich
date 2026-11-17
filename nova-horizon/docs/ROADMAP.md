# Development roadmap

Status is evidence-based. A checked item means code and automated checks exist; it does not imply real-device validation.

## Phase 0 — independent foundation
- [x] Isolated source subtree in the existing repository
- [x] Kotlin Android shell
- [x] Rust JNI library
- [x] Frame-time sample window and unit tests
- [x] Generic priority queue with coordinate deduplication and generation invalidation
- [x] Download state machine with monotonic progress, retries and verification transitions
- [x] Validated Mojang version manifest parser and hostile-host tests
- [x] Official manifest HTTPS retrieval from Android
- [x] Real EGL/OpenGL ES context probe
- [x] Android ABI, CPU, memory and thermal diagnostics
- [x] ARM64 debug CI build definition
- [x] Successful end-to-end Android ARM64 debug APK CI build (GitHub-hosted runner; not physical device)

## Phase 1 — device and graphics capability inventory
- [x] CPU ABI and logical core inventory
- [x] EGL/OpenGL ES capability probe
- [x] Device GPU renderer/vendor identification through GL context
- [x] Public Android Vulkan feature flag (not Vulkan device creation)
- [ ] Vulkan instance/device/queue/extension probe
- [ ] Mali driver-specific validation on physical hardware
- [ ] Perfetto trace collection and repeatable benchmark harness

## Phase 2 — installation and account foundation
- [x] Public official version index retrieval and native validation
- [x] Full official version list, search and selection in Android UI
- [x] Per-version metadata retrieval with official-index SHA-1 verification and Rust schema validation
- [x] Download state model with retry/verification transitions
- [x] Single-artifact downloader with trusted HTTPS hosts, size and SHA-1 validation
- [x] Resumable HTTP Range transfers guarded by strong ETag / If-Range
- [x] Private staging, fsync and atomic file promotion
- [x] Android 14+ user-initiated transfer job and older Android WorkManager fallback
- [x] Conservative client JAR, ordinary library JAR and asset-index install plan
- [x] Asset-index validation and deduplicated asset-object expansion
- [x] Bounded-concurrency asset batch transfer with resumable, SHA-1-verified objects
- [x] Legacy virtual-assets/resources materialization using hard links or verified copies
- [x] Download scheduling connected to the version UI and gated by Java entitlement
- [ ] End-to-end downloader tests against controlled HTTP range/ETag server
- [ ] Complete platform-native classifier resolution for Android/Bionic
- [ ] Keystore-backed token storage audit
- [ ] Offline launcher state machine

## Phase 3 — Java runtime research and integration
- [ ] Select and audit a redistributable ARM64 Java runtime
- [x] Parse Mojang modern and legacy game/JVM argument metadata with ordered OS/feature rules
- [x] Build a shell-free JVM argv and ProcessBuilder launch boundary (not yet connected to a JVM runtime)
- [ ] Verify JVM lifecycle and JNI/native library loading
- [ ] Define graphics and input bridge requirements
- [ ] Compatibility matrix for Minecraft versions
- [ ] No launch button until end-to-end runtime tests pass

## Phase 4 — game integration
- [ ] Official game file installation validation on device
- [x] Version-specific argument parsing and placeholder resolution
- [ ] Complete version-specific launch configuration (classpath, natives, authentication and runtime integration)
- [ ] Rendering and input integration
- [ ] Audio integration
- [ ] World save and resume validation
- [ ] Touch controls and external input
- [ ] Resource packs and compatible mod-loader handling

## Phase 5 — performance and release
- [ ] Repeatable benchmark scene and trace protocol
- [ ] CPU/GPU/RAM/frame-time profiling on physical hardware
- [ ] Thermal soak test
- [ ] Security and license audit
- [ ] Signed release workflow after signing configuration is verified
