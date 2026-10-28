# Android updates without uninstalling / Обновления без удаления

## Важный факт о v1.0.0

Ранее GitHub Actions создавал **новый случайный debug.keystore для каждой сборки** (так устроен upstream `tools/android_build.py`).
Поэтому опубликованная v1.0.0 может иметь другую подпись, чем следующая сборка. Изменение только versionName/versionCode этого не исправляет.
Для сохранения установки v1.0.0 требуется **тот же самый приватный ключ**. Если он не был сохранён, его невозможно восстановить из APK.
Начиная с первой сборки, подписанной **постоянным ключом**, последующие обновления смогут устанавливаться поверх неё без удаления.

## Настройка один раз владельцем репозитория

1. На безопасном локальном компьютере с установленным JDK выполните:
   ```bash
   keytool -genkeypair -v -keystore horizon-updates.keystore -alias androiddebugkey -keyalg RSA -keysize 3072 -validity 10000 -storepass android -keypass android -dname "CN=Horizon Android by Vanich"
   base64 -w 0 horizon-updates.keystore > horizon-updates.base64.txt
   ```
   На Windows вместо `base64 -w 0` используйте PowerShell:
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("horizon-updates.keystore")) | Set-Content horizon-updates.base64.txt
   ```
2. GitHub → репозиторий → **Settings → Secrets and variables → Actions → New repository secret**.
3. Название: `HORIZON_SIGNING_KEYSTORE_B64`. Значение: содержимое `horizon-updates.base64.txt` целиком, без переносов строк.
4. **Надёжно сохраните** исходный `horizon-updates.keystore` в защищённом резервном хранилище. Никогда не коммитьте ключ и base64 в GitHub.
5. Запустите workflow **Android test APK (no release)**. Он откажется собирать APK без секрета, вместо того чтобы незаметно создавать новую подпись.
6. Перед следующей публикацией измените `versionCode` на число больше предыдущего (26, 27...) и `versionName` (1.0.1, 1.0.2...) в `tools/apply_release_polish.py`. Пакет `dev.horizon.android` не меняйте.

В будущем APK, подписанные одним постоянным ключом, будут устанавливаться поверх друг друга, если package name совпадает, versionCode растёт и устройство принимает пакет. Миры и настройки при штатном обновлении сохраняются.

**Внимание:** первая миграция с v1.0.0 на APK с новым постоянным ключом всё ещё потребует резервного копирования и переустановки. Не удаляйте старое приложение до экспорта миров.
