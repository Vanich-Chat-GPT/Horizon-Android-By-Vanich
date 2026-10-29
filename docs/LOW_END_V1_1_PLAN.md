# Horizon Android v1.1.0 — Low End performance and release checklist

**Status: in development; do not publish as stable until tests pass.**

## Implemented in source (requires CI/device validation)
- Eco preset: 50% render scale, 4 render chunks, 4 simulation chunks, reduced entity distance and weather radius.
- Balanced preset: 67% render scale, 7 render chunks, 5 simulation chunks.
- Android streaming result consumption capped at 24 items per frame, from 48. This bounds main-thread processing time, **not total queue memory**. It can delay chunk appearance; test for backlogs.
- Launcher: Minecraft-inspired block button corners and lightweight batched pixel landscape, while retaining Material You palette and touch hitboxes.
- Android versionName 1.1.0 and versionCode 26, same package ID and signing workflow.

## Not yet implemented
- Background download foreground service, progress notification, completion notification, and recovery after process death.
- Real animated panorama and polished settings/profile/loading pages.
- Bounded queue size / memory-aware chunk cache eviction; current per-frame cap is **not** a RAM cap.
- Profiling-driven GPU allocations, resource streaming and buffer reuse.

## Acceptance tests before publishing
1. GitHub Actions ARM64 release build completes and produces a signed installable APK.
2. APK installs as update on same-package, same-certificate, lower-versionCode build.
3. Test on 4 GB RAM Android: capture Android PSS/RSS before launch, in menu, and after 10 minutes moving through new terrain. Check for rising memory usage and OOM.
4. Compare 1% low frame rate and frame-time p95/p99 for identical seed, graphics, view distance and 5-minute route. FPS gain cannot be claimed without results.
5. Run world load/unload 10 times; test touch editor, Cyrillic, offline play, Wi-Fi interruption and app resume.
6. For background downloads: show real downloaded bytes / total when known; notification permission on Android 13+; foreground service type and OS restrictions; cancellation/retry and completion/failure messages. **Never claim background download is supported until implemented and tested.**

**Safety:** backup Minecraft worlds before any signing-key migration from old v1.0.0 APK.
