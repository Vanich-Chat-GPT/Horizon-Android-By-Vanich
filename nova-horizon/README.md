# NOVA HORIZON

Самостоятельный Android-проект для исследования и разработки легального запуска Minecraft Java Edition на ARM64.

> Текущий статус: **independent bootstrap / ранняя разработка**. Это не готовый Minecraft-клиент. На этом этапе есть Android-оболочка, Rust JNI-модуль, измерение frame-time и независимая очередь фоновых задач. JVM, графический мост, официальный загрузчик, Microsoft OAuth и запуск Minecraft ещё не реализованы.

## Принципы

- Исходники этого каталога написаны отдельно. Код, скрипты и бинарные файлы Horizon, Starling, PojavLauncher и других портов не используются.
- Не включаем игровые файлы, библиотеки или ресурсы Minecraft в APK.
- Используем только законно полученные игровые файлы и официально разрешённую авторизацию.
- Не подделываем токены и не обходим лицензионные проверки.
- Не называем тестовые сцены Minecraft и не показываем фиктивные статусы установки.
- Не обещаем FPS или совместимость без измерений на реальном устройстве.
- Основной ABI на старте: `arm64-v8a`.

## Структура

- `app/` — Kotlin + Jetpack Compose Android application.
- `core/` — независимое Rust-ядро и JNI bridge.
- `docs/` — архитектура, безопасность, этапы и тестовая матрица.
- `THIRD_PARTY_NOTICES.md` — реестр используемых инструментов и зависимостей.

## Сборка

Требуются JDK 17, Android SDK/NDK, Gradle 8.13 и Rust stable.

Из каталога `nova-horizon`:

```bash
cargo test --manifest-path core/Cargo.toml
cargo fmt --manifest-path core/Cargo.toml -- --check
cargo clippy --manifest-path core/Cargo.toml --all-targets -- -D warnings
cargo ndk -t arm64-v8a -o app/src/main/jniLibs build --manifest-path core/Cargo.toml --release
gradle assembleDebug
```

CI выполняет те же проверки и собирает debug APK. Debug APK не является стабильным подписанным релизом.

## Важное архитектурное ограничение

Minecraft Java Edition — большая Java-программа, использующая JVM, LWJGL и графические/системные API. Самостоятельный лаунчер и Rust-подсистемы не заменяют JVM и совместимый runtime. Поддержка реальной игры требует отдельной реализации и проверки Java runtime, нативных библиотек, оконно-графического слоя, ввода и сетевого окружения. До завершения этих работ кнопка запуска не активируется.

## Лицензия

Исходники NOVA HORIZON распространяются под GPL-3.0-only. Minecraft, Mojang, Microsoft и соответствующие товарные знаки принадлежат их правообладателям.
