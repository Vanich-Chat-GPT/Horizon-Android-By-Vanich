# NOVA HORIZON game engine integration

The Android game-runtime layer is built from the pinned **Amethyst-Android** source tree:

- Upstream: https://github.com/AngelAuraMC/Amethyst-Android
- Pinned upstream commit: \`166af615dbdca1a507b8c2d379822cca02795132\`
- License: GNU LGPL-3.0
- CI checks out the source and all native submodules, then applies the branding/package patch in \`prepare_amethyst.py\`.

This integrates a proven Android Java Edition engine instead of a placeholder JVM stub. It supplies the Android OpenJDK runtime manager, Minecraft version installation/launch pipeline, LWJGL/GLFW Android bridge, native graphics/audio libraries, and touch-input system.

For Minecraft 1.20.1, the engine selects Java 17. The runtime manager downloads the ARM64 Java 17 runtime from the upstream Amethyst OpenJDK release repository when first needed. Actual game startup and renderer compatibility still require physical-device validation.

The CI build produces an installable debug APK named \`NOVA-HORIZON-arm64-debug.apk\`.

## License and source

Amethyst is licensed under LGPL-3.0. Its license and third-party notices remain in the upstream source checkout used for the build. The pinned source revision is publicly available at:

https://github.com/AngelAuraMC/Amethyst-Android/tree/166af615dbdca1a507b8c2d379822cca02795132

The NOVA HORIZON branding patch is maintained in this repository.
