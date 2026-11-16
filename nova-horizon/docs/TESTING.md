# Testing strategy

## Automated checks
- Rust unit tests: `cargo test`
- Formatting: `cargo fmt --check`
- Lints: `cargo clippy --all-targets -- -D warnings`
- Android ARM64 debug build through GitHub Actions
- APK package/ABI inspection after the first successful build

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

No physical-device results are claimed by CI.
