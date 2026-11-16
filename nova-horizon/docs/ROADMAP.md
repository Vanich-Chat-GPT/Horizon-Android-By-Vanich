# Development roadmap

Status is evidence-based. A checked item means code and automated checks exist; it does not imply real-device validation.

## Phase 0 — independent foundation
- [x] Isolated source subtree in the existing repository
- [x] Kotlin Android shell
- [x] Rust JNI library
- [x] Frame-time sample window and unit tests
- [x] Generic priority queue and unit tests
- [x] ARM64 debug CI build definition
- [ ] First successful GitHub Actions run

## Phase 1 — device and graphics capability inventory
- [ ] CPU ABI and core inventory
- [ ] EGL/OpenGL ES capability probe
- [ ] Vulkan capability probe when available
- [ ] Mali driver identification without hard-coded model assumptions
- [ ] Perfetto trace collection guide

## Phase 2 — installation and account foundation
- [ ] Official version metadata parser
- [ ] Download manifest model and hash verification
- [ ] Resumable downloads and safe staging
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
