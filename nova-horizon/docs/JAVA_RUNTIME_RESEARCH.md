# Java runtime feasibility and decision log

Status: investigation only. No third-party runtime binary has been imported or bundled.

## Why Android's built-in runtime is not sufficient

Android ART runs Android application bytecode in DEX form. The platform toolchain converts app Java/Kotlin code to DEX; it is not a general desktop Java SE runtime that can execute Minecraft's downloaded desktop JARs as-is. See the Android platform architecture documentation:
https://developer.android.com/guide/platform

NOVA's own Kotlin code runs on ART. Minecraft Java Edition needs a separately supplied Java SE-compatible runtime and the native/graphics environment expected by the selected game version.

## Candidate investigation

The OpenJDK Mobile project describes a modular VM/JDK architecture, but its Android platform page currently states that Android work is still TODO and lists defining the build, differences and CI as next steps:
https://openjdk-mobile.github.io/architecture/
https://openjdk-mobile.github.io/android/

Community builds of OpenJDK for Android/Bionic exist, but a published ARM64 executable or libjvm is not evidence of compatibility with Minecraft, LWJGL, Android's sandbox, the device's API level, or Mali. Such builds are investigation leads only. They must not be downloaded into the APK or treated as a supported runtime without source review, license review, reproducible build evidence, ABI/dependency inspection and device tests.

## Candidates reviewed and rejected

- `itsaky/openjdk-17-android` publishes an ARM64 Android JRE, but its latest release is dated January 2022. That is too old to accept as a current runtime without a fresh reproducible build, security review, API-level checks and physical-device testing.
- `FongMi/bdj-runtime` publishes an ARM64 OpenJDK 8 Zero runtime candidate. Its own validation says testing was on an Android API 34 x86 emulator using ARM translation, not a physical ARM64 device. Its source notice also identifies an Android compatibility patch collection based on PojavLauncher adaptations. That directly conflicts with NOVA's no-launcher-code-reuse rule, so none of its source, patches or binaries will be imported.
- Other Android OpenJDK builds derived from PojavLauncher adaptations are excluded for the same reason, regardless of whether their binary could start.

These candidates are research findings only. No runtime archive or launcher implementation was copied into NOVA.

## Required runtime acceptance gates

1. Pin the exact OpenJDK source revision, patches, boot JDK, NDK, build tools and every external source archive by SHA-256.
2. Verify license notices and the full license of every patch and bundled class/native library.
3. Build an ARM64/Bionic runtime reproducibly; inspect ELF interpreter, NEEDED libraries, API-level requirements, page-size compatibility and executable-memory behavior on Android.
4. Run the JVM from the app's private storage with no shell/terminal dependency.
5. Test Java 17 and/or Java 21 compatibility for the initial Minecraft version profile, including class loading, TLS, ZIP, fonts, audio and thread lifecycle.
6. Separately prove that the selected Minecraft version's LWJGL native libraries can be loaded and that window, input, audio and OpenGL/EGL calls can be bridged to Android.
7. Run a legally obtained, unmodified client JAR end-to-end, then verify pause/resume, world saves and offline launch.
8. Repeat on a physical ARM64/Mali device and record failures rather than assuming desktop Linux results transfer to Android.

## Architecture decision

Do not bundle an unverified runtime yet. Keep the JVM boundary separate from the Android app and Rust Core. Start with a single pinned Minecraft version and its required Java major version; widen the compatibility matrix only after the first native/game end-to-end path is demonstrated.

A Java runtime alone is insufficient. The desktop launcher metadata also selects native libraries, while Minecraft's desktop graphics/window/input path is coupled to LWJGL/GLFW. Those native components need a separately validated Android/Bionic implementation or an independently developed compatibility layer. Do not claim full game support while that bridge is absent.
