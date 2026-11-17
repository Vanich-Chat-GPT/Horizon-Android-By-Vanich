# NOVA HORIZON

Android-сборка **Horizon — Minecraft: Java Edition 26.3, переписанного на Rust**. Это не Java-лаунчер для старых версий Minecraft и не Pojav/Amethyst.

## Реальная игровая основа

- Android-порт: [MocLG/horizon-android](https://github.com/MocLG/horizon-android)
- Игровой Rust-проект: [horizon-rust/horizon](https://github.com/horizon-rust/horizon)
- Зафиксированный upstream commit Android-порта: `1788803beebf105abe58de72752d08a5f0e0ee76`
- Игра собирается как нативная ARM64-библиотека `libhorizon.so`; Java 25 используется только для подготовки ресурсов, а не как игровой движок.
- Графический backend Android-порта требует Vulkan 1.1 и Android 10+.
- В APK должны присутствовать Rust-игра, Android Java helper, JRE 25 и подготовочные ресурсы.

## Сборка NOVA HORIZON

CI клонирует закреплённую версию настоящего Android-порта, применяет узкий брендинг-патч (название приложения, package ID и endpoint обновлений), затем выполняет upstream `android/build.sh`.

- ABI: `arm64-v8a`
- Package ID: `dev.nova.horizon`
- Название приложения: `NOVA HORIZON`
- Целевая игра: Minecraft Java Edition 26.3, Rust Horizon
- Результат CI: `NOVA-HORIZON-26.3-arm64.apk` и SHA-256
- Сборка CI подписывается временным debug-ключом и предназначена для установки и проверки; это пока не постоянная release-подпись.

Сборка запускается workflow **NOVA HORIZON — Horizon Rust 26.3 Android**. Проверка упаковки подтверждает наличие Rust game library, Java helper, JRE и игровых подготовочных ресурсов. Она сама по себе не заменяет запуск на физическом планшете.

## Установка игры

Для загрузки Minecraft 26.3 требуется собственная легально приобретённая копия Minecraft: Java Edition и вход через Microsoft-аккаунт, владеющий игрой. Сам Horizon не содержит игровые бинарные файлы, текстуры или звуки Mojang.

## Совместимость устройства

Целевое устройство проекта — Redmi Pad SE 8.7 (MediaTek Helio G85 / Mali-G52 MC2, ARM64, Android 16). Важна фактическая поддержка Vulkan 1.1 драйвером устройства: наличие ARM64 само по себе этого не гарантирует. До проверки APK на самом планшете совместимость и FPS не объявляются подтверждёнными.

## Разработка

`nova-horizon/app` и `nova-horizon/core` содержат раннюю самостоятельную оболочку/экспериментальный Rust-модуль из предыдущего прототипа. Они не являются игровым движком Horizon 26.3 и не используются новым Android workflow. Рабочая игровая основа берётся из закреплённого upstream-проекта; дальнейшие изменения лаунчера и оптимизации нужно переносить именно в этот слой.

## Лицензии и атрибуция

NOVA HORIZON — неофициальная сборка. Android-порт и Horizon распространяются по лицензиям исходных проектов; OpenJDK runtime имеет отдельные лицензионные условия. Mojang и Microsoft не связаны с проектом. См. `THIRD_PARTY_NOTICES.md`.
