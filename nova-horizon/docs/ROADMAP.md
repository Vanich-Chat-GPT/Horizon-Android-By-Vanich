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
- [ ] First successful end-to-end Android ARM64 APK CI run

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
- [x] Download state model (not yet a network/file downloader)
- [ ] Per-version metadata retrieval and schema validation
- [ ] Download manifest model and SHA-1/SHA-256 verification
- [ ] Resumable downloads, cancellation and safe staging
- [ ] Microsoft OAuth authorization-code flow with PKCE
- [ ] Keystore-backed token storage
- [ ] Offline launcher state machine

## Phase 3 — Java runtime research and integration
- [ ] Select and audit a redistributable ARM64 Java runtime
- [ ] Verify JVM lifecycle and JNI/native library loading
- [ ] Define graphics and input bridge requirements
- [ ] Compatibility matrix for Minecraft versions
- [ ] No launch button until end-to-end runtime tests pass

## Phase 4 — game integration
- [ ] Official game file installation
- [ ] Version-specific launch configuration
- [ ] Rendering and input integration
- [ ] World save and resume validation
- [ ] Touch controls and external input
- [ ] Resource packs and compatible mod-loader handling

## Phase 5 — performance and release
- [ ] Repeatable benchmark scene and trace protocol
- [ ] CPU/GPU/RAM/frame-time profiling on physical hardware
- [ ] Thermal soak test
- [ ] Security and license audit
- [ ] Signed release workflow after signing configuration is verified
