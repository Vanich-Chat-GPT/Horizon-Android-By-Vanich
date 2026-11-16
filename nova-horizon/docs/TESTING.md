# Testing strategy

## Automated checks
- Rust unit tests: cargo test
- Formatting: cargo fmt --check
- Lints: cargo clippy --all-targets -- -D warnings
- Official manifest parser tests, including malformed IDs, duplicate IDs, invalid hashes and untrusted metadata hosts
- Android ARM64 debug build through GitHub Actions
- APK package/ABI inspection after successful build

## Official catalog validation
- The Android client fetches only the official Mojang public version index over HTTPS.
- Redirects are limited and restricted to the same official host.
- Response size is capped before UTF-8 decoding.
- Rust Core validates identifiers, duplicate entries, SHA-1 shape, official metadata URL prefix and latest-version references.
- Catalog presence is not proof of game-file installation, entitlement or runtime compatibility.

## Physical-device matrix
Record device model, Android build, ABI, SoC, GPU/driver, available RAM, battery state and ambient/thermal state.

For every performance comparison, keep constant:
- game version and world;
- camera position and movement path;
- render distance and graphics settings;
- display refresh rate;
- background applications;
- thermal starting condition.

Report:
- average FPS;
- 1% low and 0.1% low where sampling is reliable;
- frame-time p50/p95/p99;
- peak and steady-state RAM;
- chunk task queue wait and service times;
- temperature/thermal status;
- crashes, ANRs and data integrity.

No physical-device results are claimed by CI. The current Android app has no integrated Minecraft runtime, so it cannot yet produce meaningful in-game FPS or chunk benchmarks.
