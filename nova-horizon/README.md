# NOVA HORIZON

**NOVA HORIZON 3** — неофициальная Android-сборка Horizon, Minecraft: Java Edition 26.3, переписанного на Rust. Игровой цикл и рендерер нативные; это не запуск обычного Java-клиента через Pojav/Amethyst.

## Игровая основа и Android-порт

- Horizon: [horizon-rust/horizon](https://github.com/horizon-rust/horizon) — Rust-реализация Minecraft Java 26.3.
- Android-порт и развитая мобильная оболочка: [scpao5/starling](https://github.com/scpao5/starling), продолжение Android-порта Horizon.
- Закреплённый upstream commit: `50e0ef409738310524e18f77aa8ee6c4378987ed`.
- Vulkan/wgpu rendering, NativeActivity, Android audio/input bridge, экранные контролы и редактор раскладки.
- Android diagnostics: логи, сведения о завершении процесса, экспорт отчёта и CPU/GPU/frame profiling.
- Установка и подготовка ресурсов из собственной копии Minecraft 26.3; игровых файлов Mojang в APK нет.

## NOVA HORIZON identity

- Package ID: `dev.nova.horizon`
- App label: `NOVA HORIZON`
- Version: `3.0.0`
- ABI: `arm64-v8a`
- Build profile: Cargo `fast` (оптимизированная сборка для распространения и измерений)
- APK: `NOVA-HORIZON-26.3-arm64.apk`

Сборка изменяет package/JNI namespace, launcher branding и версию, сохраняя upstream игровой код и лицензионные файлы. Тестовая APK подписывается стабильным публичным тестовым ключом upstream, а не приватным production-ключом. Поэтому это тестовая сборка, не финальная защищённая release-подпись.

## Запуск игры

Нужна собственная легально приобретённая копия Minecraft: Java Edition 26.3 и Microsoft-аккаунт, владеющий Java Edition, для загрузки официальных файлов Mojang. APK не включает клиент, сервер, текстуры, звуки или другие проприетарные игровые данные.

После установки: войти в аккаунт, дать лаунчеру подготовить ресурсы и нажать Play. Первичная подготовка занимает время; оставь приложение открытым до её завершения.

## Производительность и совместимость

Android-порт требует ARM64, Android 8+ и Vulkan. Успешная сборка APK не доказывает, что конкретный GPU-драйвер устройства работает без ошибок.

Профиль `fast` включает оптимизированную компиляцию Rust. В игровом коде уже есть отдельные worker threads, обработка входящих chunk packets с бюджетом времени кадра и лимиты загрузки мешей. В Android Diagnostics есть измерения frame time, CPU/GPU, памяти, температуры и очередей. Это исходная база для реальной оптимизации, а не обещание фиксированных 90 FPS.

Цель настройки на Redmi Pad SE 8.7 — стабильная частота кадров без искусственного ограничения RAM и без снижения качества ближней картинки. Изменения дальних чанков допускаются отдельно. FPS, нагрев, память и загрузка чанков нужно измерить на самом планшете; результаты с других GPU не переносятся напрямую.

## Что ещё требует проверки

- Установка и первый запуск на Redmi Pad SE 8.7.
- Вход Microsoft и получение официальных игровых файлов.
- Создание/загрузка мира, сохранение и повторный запуск.
- Touch controls, клавиатура/IME, звук, сворачивание/возврат.
- Vulkan driver stability, frame pacing, thermal throttling и память.
- Проверка обновления APK поверх предыдущей сборки и сохранения миров.

## Разработка

Workflow **NOVA HORIZON — Rust 26.3 Android ARM64** клонирует закреплённый upstream commit, применяет branding/JNI patch, собирает оптимизированный ARM64 APK и проверяет package ID, native library, Android helpers, preparation kit, alignment и APK signature. Crash symbols загружаются отдельным CI artifact.

## Лицензии и атрибуция

Android-порт Starling и игровой проект Horizon распространяются по MIT; сторонние компоненты сохраняют собственные лицензии. NOVA HORIZON не связан с Mojang или Microsoft. См. `THIRD_PARTY_NOTICES.md`.
