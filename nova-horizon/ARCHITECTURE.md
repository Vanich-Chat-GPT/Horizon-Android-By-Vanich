# NOVA HORIZON — архитектура Android-порта

## Источник игрового движка

NOVA HORIZON собирается поверх Android-порта [MocLG/horizon-android](https://github.com/MocLG/horizon-android), закреплённого на commit `1788803beebf105abe58de72752d08a5f0e0ee76`. Сам игровой проект — [horizon-rust/horizon](https://github.com/horizon-rust/horizon): реализация Minecraft Java Edition 26.3 на Rust.

Это нативная игра, а не запуск Java-клиента Minecraft через JVM/LWJGL. Java 25 включена для запуска подготовочных инструментов Mojang при импорте ресурсов; игровой цикл работает в Rust.

## Слои

1. **Android launcher** — нативное окно, настройки, Microsoft sign-in, импорт/подготовка файлов, touch controls, обновления.
2. **Rust Horizon client** — игровой цикл, мир, чанки, сущности, сеть, ввод и рендеринг.
3. **Android platform bridge** — JNI/NativeActivity, клавиатура, буфер обмена, датчики, системные пути и lifecycle.
4. **Vulkan/wgpu** — графический backend Android-порта. Минимальное требование манифеста — Vulkan 1.1.
5. **JRE 25 + horizon-prepare** — подготовка совместимых ресурсов из собственной копии Minecraft; не является runtime самого игрового движка.

## Сборка

Workflow скачивает закреплённый upstream commit, применяет проверяемый брендинг-патч и запускает `android/build.sh`. Верификация APK проверяет package ID и наличие Rust-библиотеки, Java helper и архивов JRE/ресурсов.

## Ограничения проверки

- Успешная компиляция не доказывает корректный запуск на каждом GPU-драйвере.
- Vulkan 1.1 проверяется на целевом устройстве отдельно.
- FPS, frame pacing, нагрев и загрузка чанков измеряются только на физическом устройстве.
- Произвольный жёсткий лимит RAM не вводится.
- Ближнее качество изображения не ухудшается без отдельного согласования.
