# NOVA HORIZON — архитектура

## Игровой движок

NOVA HORIZON использует Horizon — нативную Rust-реализацию Minecraft Java Edition 26.3. Для Android используется развитый Android-порт из проекта Starling, продолжающий Android-ветку Horizon. Закреплённый исходный commit: `50e0ef409738310524e18f77aa8ee6c4378987ed`.

Это не Java Edition, запущенная через JVM/LWJGL. Основной игровой цикл и рендеринг реализованы в Rust. Java 25 используется Android helper-процессом для подготовки ресурсов из собственной копии игры.

## Слои

1. **Android home launcher** — брендированный v3 экран, импорт файлов через системный picker, запуск игрового Activity.
2. **Rust Horizon client** — мир, чанки, сущности, игровая логика, сеть, ввод и рендеринг.
3. **Android platform bridge** — JNI, lifecycle, NativeActivity, touch/mouse/keyboard, clipboard, системные папки, аудио и foreground work.
4. **Vulkan + wgpu** — графический backend Android.
5. **Touch controls** — мобильные схемы управления, редактор расположения/размера/прозрачности; статичный джойстик — начальный режим, плавающий доступен переключением.
6. **Diagnostics** — логи, crash/exit information, CPU/GPU/frame timing, память, температура и экспорт локального ZIP-отчёта.
7. **Foreground notification** — актуальная строка задачи и скорость входящего сетевого трафика UID, вычисленная по TrafficStats.

## Локализация

Новые профили по умолчанию используют `ru_ru`. Базовые 1055 русских строк Horizon Android объединяются с русскими строками текущего Android-порта; дополнительно переведены новые аккаунтные, shader-pack, control-hub и launcher UI ключи. Оригинальный английский остаётся fallback для новых ключей, для которых перевод ещё не добавлен.

## Сборка

Workflow скачивает закреплённый upstream commit, применяет branding/JNI namespace patch и `nova-horizon/ui/integrate_launcher.py`, затем выполняет `python packaging/android/build_apk.py --abi arm64-v8a --profile fast`. Используются JDK 25, Rust stable, cargo-ndk, Android platform 36 и NDK 28.2.13676358.

CI проверяет Android Python tests, diagnostics harness, mobile graphics defaults, package ID `dev.nova.horizon`, label `NOVA HORIZON`, ARM64 game library, Android helper libraries, preparation kit, launcher background, 16 KB alignment и подпись APK.

## Производительность

Мобильные настройки NOVA HORIZON ограничивают кадровую частоту 90 FPS и не уменьшают разрешение рендера или базовые эффекты ближней картинки. На менее мощных уровнях сокращаются дальность симуляции/отрисовки и детализация дальнего ландшафта. Искусственный жёсткий лимит RAM не вводится.

До измерений на планшете нельзя утверждать, что достигнуты 90 FPS или устранены все просадки. Нужно снять одинаковые сцены: FPS/1% low, CPU/GPU frame time, время загрузки чанков, RAM/PSS, температуру и поведение после прогрева. Затем менять по одному узкому месту.

## Ограничения

- CI build success подтверждает компиляцию и упаковку, но не запуск на реальном GPU.
- Vulkan capability и драйвер проверяются на планшете.
- 90 FPS — цель настройки, не обещание.
- Первый запуск требует законно полученных игровых файлов Minecraft Java 26.3.
