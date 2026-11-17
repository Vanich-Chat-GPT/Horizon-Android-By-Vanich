# Android ARM64 installation plan

The installer planner is deliberately conservative and does not claim launch readiness.

- It plans the version-specific client JAR and asset-index JSON after metadata validation.
- It includes a library's ordinary JAR only when the parser can safely resolve the metadata path and its ordered Mojang rules allow the Android ARM64 profile.
- Unknown rule conditions are not treated as an allow decision.
- Desktop native classifiers are recorded as unresolved requirements; Linux, Windows and macOS binaries are never relabelled as Android/Bionic.
- The asset index is downloaded and validated, then expanded into deduplicated content-addressed asset objects.
- Asset objects are downloaded with bounded concurrency, individual SHA-1 verification and resumable staging.
- Legacy virtual-assets and resources layouts are materialized with hard links when supported, otherwise with verified copies.
- Download scheduling is gated by the Microsoft account's Java Edition entitlement.
- The plan always returns launchReady=false until a compatible Java SE runtime, native-library bridge, renderer and input/audio integration pass end-to-end checks.

## Remaining installation work

1. Resolve and validate Android/Bionic native classifiers instead of selecting desktop binaries.
2. Validate complete installs on a physical ARM64 device and verify every installed file against official metadata.
3. Add controlled-server tests for interrupted/resumed transfers, ETag changes, checksum failures and cancellation.
4. Produce a version-specific runtime launch configuration only after the Java runtime and native bridge are accepted.
