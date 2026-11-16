# CI verification log

This file records actual automated validation, not release claims.

- Rust formatting, unit tests and Clippy are enforced in the NOVA-only workflow.
- The Android job builds the Rust cdylib for arm64-v8a, assembles an Android debug APK, then inspects the package ID and bundled native ABI.
- A failed workflow must be debugged from its job logs and corrected on this branch before an APK artifact can be described as built.
- GitHub-hosted runner results do not substitute for installation, launch, performance or thermal tests on the Redmi Pad SE 8.7.
- Production signing and Releases are intentionally disabled until the permanent signing key is configured and all functional acceptance gates are met.
