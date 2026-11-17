# NOVA HORIZON — архитектура

## Игровой движок

NOVA HORIZON использует Horizon — нативную Rust-реализацию Minecraft Java Edition 26.3. Для Android используется развитый Android-порт из проекта Starling, продолжающий Android-ветку Horizon. Закреплённый исходный commit: `50e0ef409738310524e18f77aa8ee6c4378987ed`.

Это не Java Edition, запущенная через JVM/LWJGL. Основной игровой цикл и рендеринг реализованы в Rust. Java helper используется в Android-процессе подготовки ресурсов из собственной копии игры.

## Слои

1. **Android launcher / setup** — NativeActivity, вход Microsoft, импорт файлов, установка и подготовка игровых ресурсов.
2. **Rust Horizon client** — мир, чанки, сущности, игровая логика, сеть, ввод и рендеринг.
3. **Android platform bridge** — JNI, lifecycle, NativeActivity, touch/mouse/keyboard, clipboard, системные папки, аудио и foreground work.
4. **Vulkan + wgpu** — графический backend Android.
5. **Touch controls** — мобильные схемы управления, редактор расположения/размера/прозрачности и обработка жестов.
6. **Diagnostics** — логи, crash/exit information, CPU/GPU/frame timing, память, температура и экспорт локального ZIP-отчёта.

## Сборка

Workflow скачивает закреплённый upstream commit, применяет branding/JNI namespace patch и выполняет `python packaging/android/build_apk.py --abi arm64-v8a --profile fast`. Используются JDK 25, Rust stable, cargo-ndk, Android platform 36 и NDK 28.2.13676358.

CI проверяет:
- Package ID `dev.nova.horizon` и label `NOVA HORIZON`.
- ARM64 game library и Android Java helper libraries.
- preparation kit и ресурсы интерфейса.
- 16 KB alignment и подпись APK.
- SHA-256 и отдельный symbols artifact для анализа нативных сбоев.

## Производительность

Профиль `fast` — оптимизированная сборка, а не debug/quick. Android-порт уже ограничивает работу с входящими chunk packets на кадр, выполняет декодирование на отдельном потоке и использует worker pool, оставляя CPU-время рендеру и системным потокам.

Нельзя считать настройки другого устройства подходящими Redmi Pad SE 8.7. Сначала нужно снять исходные показатели в одинаковой сцене: FPS/1% low, CPU/GPU frame time, время загрузки чанков, RAM/PSS, температуру и поведение после прогрева. После этого менять по одному узкому месту. Искусственный лимит RAM не вводится; качество ближней картинки не ухудшается без отдельного согласования.

## Ограничения

- CI build success подтверждает компиляцию и упаковку, но не запуск на реальном GPU.
- Vulkan capability и драйвер проверяются на планшете.
- 90 FPS — цель измерений, не обещание: фактический результат зависит от сцены, температуры, драйвера и нагрузки.
- Первичный запуск требует законно полученных игровых файлов Minecraft Java 26.3.
