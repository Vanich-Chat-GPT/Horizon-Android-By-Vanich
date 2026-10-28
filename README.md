> **📌 ЗАКРЕПЛЕНО / PINNED — Minecraft Java on Android Native v1.0.0**
>
> **[Скачать полный релиз APK (Android ARM64)](https://github.com/Vanich-Chat-GPT/Horizon-Android-By-Vanich/releases/tag/v1.0.0-minecraft-java-android-native)**
>
> Если уже установлена старая версия, **сначала сделайте резервную копию миров и настроек**. Из-за различий подписи может потребоваться удалить старую версию перед установкой новой.

---

# Minecraft Java on Android Native — Horizon Android by Vanich

**Minecraft Java Edition on Android ARM64 — native Rust/Vulkan client.**

**Полноценная версия 1.0 (сборка-кандидат):** [GitHub Releases](https://github.com/Vanich-Chat-GPT/Horizon-Android-By-Vanich/releases)

> **Важное предупреждение об установке:** если новая APK не устанавливается поверх старой версии из-за несовпадения подписи, необходимо **сначала сохранить миры, профили и настройки**, затем удалить старую установку Horizon Android и установить новую APK. Удаление приложения может удалить его локальные данные. Не удаляйте старую версию до резервного копирования.

### Управление и оформление

- В игре в правом верхнем углу — кнопка с пальцем ☝, открывающая редактор сенсорных кнопок.
- Перетаскивание, размер, прозрачность, добавление/удаление, назначение клавиш, видимость, сетка 2,5%, сохранение и сброс раскладки.
- Material You: системный цвет обоев Android 12–16, скруглённые кнопки и анимированная подсветка нажатий. Пиксельный подзаголовок Java Edition в стиле Minecraft.
- Русский язык расширен для настроек управления, подсказок лаунчера и выбора параметров. Часть системных и игровых строк по-прежнему может оставаться на английском.
- Оптимизации чанков и графические профили предыдущих сборок сохранены.

**Важно:** внешний вид редактора разработан для Horizon, а не скопирован из Minecraft Bedrock. Поддерживаются аналогичные базовые действия, но не гарантируется идентичность всех настроек и анимаций.

---

> **📌 ЗАКРЕПЛЕНО / PINNED TEST BUILD — TOUCH + FPS**
>
> [**Скачать последнюю тестовую сборку с настройкой кнопок и оптимизацией чанков**](https://github.com/Vanich-Chat-GPT/Horizon-Android-By-Vanich/releases/tag/android-touch-fps-test-2026-10-29)
>
> Предыдущая тестовая версия (Pre-release) сохранена для сравнения. Новая v1.0.0 — в закреплённой ссылке выше.
>
> ---

# Horizon Android by Vanich

Native Android ARM64 Minecraft Rust client development, based on the Horizon Rust game engine (GPL-3.0).

**Status: user-approved v1.0.0 full Release build in GitHub Actions; actual device testing still recommended.** This repository is a source *overlay*, not a second copy of the proprietary Minecraft game or a stand-alone playable game. The GitHub Actions workflow clones upstream, applies the overlay, downloads verified game metadata and compiles a native Android APK.

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

## Touch customization and smooth chunk-loading test

The Android build now applies `tools/apply_touch_performance.py` after the launcher overlay. This extends the **real in-game** touch editor: drag a control with a finger, select **Size** or **Opacity**, drag the slider, choose **Apply to all** when desired, optionally toggle **Grid 2.5%**, and press **Done**. **Cancel** restores the original layout. Settings are stored in `horizon-touch.json` per game profile. Original custom buttons remain supported; controls can be enlarged up to the updated supported bounds.

Launcher Settings includes **Touch customization** as an entry-point hint, and **Graphics preset** adjusts actual Minecraft options. The Economy / Balanced / Quality presets select render scale 50% / 67% / 90%, render distance 5 / 8 / 12 chunks, simulation distance 5 / 6 / 8 chunks, and limit some expensive video effects. The Balanced mode uses a 90 FPS *cap*, not a performance guarantee.

**Engine-level Android-specific frame pacing:** chunk streaming intake is bounded to 48 worker completions per update, rather than draining an arbitrarily large result queue in one frame. Jobs stay queued safely until a later update; this can improve frame-time stability at the cost of slower display of very distant chunks under heavy generation. Desktop keeps its original path. This is a targeted stutter mitigation, not a measured FPS result. Validate with real-world frame-time traces and memory measurements.

No new GitHub Release is created automatically by this development overlay; APK builds are uploaded as temporary Actions artifacts for review first.
