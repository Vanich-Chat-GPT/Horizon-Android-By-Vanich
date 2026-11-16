# ARM64 build pipeline

The NOVA HORIZON workflow is isolated from the legacy project tree.

## Toolchain

- JDK 17
- Android SDK platform 36 and build-tools 36.0.0
- Android NDK r30 (30.0.16248370)
- Rust stable targeting aarch64-linux-android
- cargo-ndk
- Gradle 8.13

## Native build

The Cargo working directory must be nova-horizon/core. From there, the JNI library is emitted into ../app/src/main/jniLibs for the arm64-v8a ABI. Do not pass a parent-relative Cargo manifest path while running cargo-ndk from a directory without Cargo.toml.

## APK verification

The CI job checks:
- APK exists and is non-empty;
- application ID is dev.nova.horizon;
- lib/arm64-v8a/libnova_core.so is packaged.

This is a debug artifact for engineering validation. It is not signed as a production release and does not include Minecraft game files.
