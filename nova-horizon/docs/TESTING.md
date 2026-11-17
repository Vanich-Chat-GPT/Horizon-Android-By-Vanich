# Testing strategy

## Automated checks
- Rust unit tests: cargo test
- Formatting: cargo fmt --check
- Lints: cargo clippy --all-targets -- -D warnings
- Official manifest parser tests, including malformed IDs, duplicate IDs, invalid hashes and untrusted metadata hosts
- Download state machine tests for legal transitions, byte-count monotonicity, retry offsets and verification
- Android ARM64 debug build through GitHub Actions
- APK package/ABI inspection after successful build
- The first version-catalog UI build passed the hosted ARM64 APK job; device installation is not yet verified

## Official catalog validation
- The Android client fetches only the official Mojang public version index over HTTPS.
- Redirects are limited and restricted to the same official host.
- Response size is capped before UTF-8 decoding.
- Rust Core validates identifiers, duplicate entries, SHA-1 shape, official metadata URL prefix and latest-version references.
- The Android UI receives the full catalogue only after Rust validation; each entry's metadata JSON must match its manifest SHA-1 before the Rust version-specific schema validator accepts it.
- Catalog presence is not proof of game-file installation, entitlement or runtime compatibility.

## Download state validation
- The Rust state machine does not perform network I/O or write files.
- Network retries preserve the last recorded byte offset; integrity retries reset it.
- A transfer cannot enter verification while a known content length remains incomplete.
- Only verified tasks can become Complete.
- The Android downloader implements HTTP Range/If-Range guarded by a strong ETag, strict Content-Range and Content-Length checks, private partial-file staging, SHA-1 verification, fsync and atomic promotion.
- These downloader paths have not yet been exercised by a controlled-server test suite or on a physical Android device; do not treat source implementation as verified runtime behaviour.

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
