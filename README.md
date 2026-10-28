# Horizon Android by Vanich

Native Android ARM64 Minecraft Java client development, based on [Vasysik/horizon-android](https://github.com/Vasysik/horizon-android) and the Horizon Rust game engine (GPL-3.0).

**Status: under active testing. No user-approved release.** This repository is a source *overlay*, not a second copy of the proprietary Minecraft game or a stand-alone playable game. The GitHub Actions workflow clones upstream, applies the overlay, downloads verified game metadata and compiles a native Android APK.

## Implemented source changes

- Russian and English native launcher labels, persistent language toggle and matching Minecraft `ru_ru` / `en_us` preference (existing user options are preserved until language is explicitly changed).
- System Android Roboto font when it supports Cyrillic; fallback to bundled font.
- Android Material You-inspired dark palette and round controls, with wallpaper-based Android system primary accent via JNI where supported.
- Android 13–16 themed adaptive launcher icon with monochrome layer.
- Real 40–100% native render surface scale, keeping a minimum menu size on very small displays.
- Economy, Balanced and Quality graphics profiles that update the *real* `options.txt`: chunks, simulation distance, particles, clouds, quality, vsync and FPS cap; plus native render scale.
- Touch layout and keyboard controls inherited from upstream's Android client; no Java emulation or placeholder launcher.
- Strict ARM64 native library check, APK archive integrity validation and upstream APK signing verification.

## Source architecture

- `tools/apply_vanich_overlay.py` — reproducible source transformation applied to the upstream Android branch.
- `.github/workflows/android-test.yml` — ARM64 source build on pushes to `main` or manual dispatch; uploads only an expiring **Actions artifact**, not a GitHub Release.
- The source overlay uses Mojang's **SHA-1-verified pinned** Minecraft 26.3 manifest for resource preparation, rather than trusting a republished unverified manifest.
- No game assets, account tokens, keystores, or generated Rust binaries are committed.

## Testing and limitations

Static source patch and formatting tests are separate from **on-device gameplay testing**. A CI success confirms compilation and APK structure; it does not by itself establish stable FPS, device driver compatibility, Cyrillic glyph coverage across every UI screen, or correctness of multiplayer on all Android 16 devices. More device testing is required.

For game controls and launcher internals, follow upstream's `docs/android.md`. ARM64 Android 16 is the primary target; lower Android versions are not the primary compatibility target. Existing Horizon licensing applies. Only the repository owner authorizes any final release.
