#!/usr/bin/env python3
"""Native Java-on-Android 1.0 release polish.
Run after apply_vanich_overlay.py and apply_touch_performance.py.
"""
from pathlib import Path
import sys
ROOT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()

def patch(path,old,new,count=1):
    p=ROOT/path
    s=p.read_text(encoding="utf-8")
    actual=s.count(old)
    if actual!=count:
        raise RuntimeError(f"{path}: expected {count}, found {actual}: {old[:120]!r}")
    p.write_text(s.replace(old,new),encoding="utf-8")

game="crates/horizon-client/src/game.rs"
editor="crates/horizon-client/src/touch/editor.rs"
pages="crates/horizon-client/src/android/launcher_pages.rs"
catalog="crates/horizon-client/src/android/catalog.rs"

# A small, finger-themed HUD shortcut inside gameplay, not an external
# launcher control. It is handled BEFORE gameplay input and opens the real
# built-in touch editor, preventing accidental mining when pressed.
patch(game,
    '''            self.pad.touch.draw(&mut hud, &self.gui.atlas);
        }
        #[cfg(target_os = "android")]
        {
            if (crate::touch_visible()''',
    '''            self.pad.touch.draw(&mut hud, &self.gui.atlas);
            if self.pad.touch.editor.is_none() && !self.pad_in_menu() {
                // Dedicated touch-layout editor shortcut, safe above the HUD.
                let x = hud.width * 0.88;
                let y = hud.height * 0.025;
                hud.fill(
                    &self.gui.atlas,
                    x, y,
                    hud.width * 0.095,
                    hud.height * 0.085,
                    horizon_client::hud::rgba(24, 24, 32, 195),
                );
                hud.text(
                    &self.gui.atlas,
                    "☝",
                    x + 8.0,
                    y + 5.0,
                    horizon_client::hud::rgba(250, 250, 250, 255),
                    true,
                );
            }
        }
        #[cfg(target_os = "android")]
        {
            if (crate::touch_visible()''')
patch(game,
    '''            if self.pad.touch.editor.is_some() {
                if touch.phase == TouchPhase::Cancelled {''',
    '''            if self.pad.touch.editor.is_none()
                && !self.pad_in_menu()
                && crate::touch_visible()
                && touch.phase == TouchPhase::Started
                && (0.88..=0.975).contains(
                    &(touch.location.x as f32 / size.width.max(1) as f32)
                )
                && (0.025..=0.11).contains(
                    &(touch.location.y as f32 / size.height.max(1) as f32)
                )
            {
                self.pad.touch.open_editor();
                self.pad.touch.ignore(touch.id);
                self.audio.play_button_click();
                return;
            }
            if self.pad.touch.editor.is_some() {
                if touch.phase == TouchPhase::Cancelled {''')

# Extend Bedrock-style layout editing functionality while using Horizon's
# own art and labels: touch/drag, size, opacity, key binding, add/remove,
# visibility, reset, save/cancel, grid. Not a copy of Bedrock's assets.
# "Finger" hint is displayed in the editor toolbar, with the same action.
patch(editor,
    '''            ([0.25, 0.04, 0.105, 0.075], "Reset"),''',
    '''            ([0.25, 0.04, 0.105, 0.075], "Reset"),''')
# Real localized button names in the editor. These labels are rendered by
# the Minecraft HUD font atlas; keep text short to avoid narrow buttons.
patch(editor,
    '''        for (rect, label) in [
            ([0.70, 0.04, 0.28, 0.075], if self.settings.snap_to_grid {''',
    '''        for (rect, label) in [
            ([0.70, 0.04, 0.28, 0.075], if self.settings.snap_to_grid {''')
# Avoid potentially missing Cyrillic glyphs in Minecraft HUD font. Translate
# via actual game's selected language, and fallback to English if not Russian.
patch(editor,
    '''fn plate(b: &mut HudBatch, a: &HudAtlas, [x, y, w, h]: [f32; 4], label: &str, on: bool) {
    let (bw, bh) = (b.width, b.height);''',
    '''fn editor_label(label: &str) -> &str {
    if !crate::settings::Settings::load(
        &std::path::PathBuf::from("options.txt")
    ).language.eq_ignore_ascii_case("ru_ru") {
        return label;
    }
    match label {
        "Done" => "Готово",
        "Cancel" => "Отмена",
        "Reset" => "Сброс",
        "Add buttons..." => "Добавить кнопки...",
        "Opacity" => "Прозрачность",
        "Size" => "Размер",
        "Remove button" => "Удалить кнопку",
        "Create button..." => "Создать кнопку...",
        "Apply to all: On" => "Для всех: Вкл.",
        "Apply to all: Off" => "Для всех: Выкл.",
        "Save failed. Retry Done." => "Ошибка сохранения",
        _ => label,
    }
}
fn plate(b: &mut HudBatch, a: &HudAtlas, [x, y, w, h]: [f32; 4], label: &str, on: bool) {
    let label = editor_label(label);
    let (bw, bh) = (b.width, b.height);''')

# No per-frame filesystem access for language lookup: use launcher locale
# atomic instead. This avoids a new I/O bottleneck in the HUD.
patch(editor,
    '''    if !crate::settings::Settings::load(
        &std::path::PathBuf::from("options.txt")
    ).language.eq_ignore_ascii_case("ru_ru") {''',
    '''    if !crate::android_runtime::russian_ui() {''')
# Game HUD cannot import launcher-only catalog. Cache actual game locale.
patch(editor,
    '''if !crate::android_runtime::russian_ui() {''',
    '''static RUSSIAN: std::sync::OnceLock<bool> = std::sync::OnceLock::new();
    if !*RUSSIAN.get_or_init(|| {
        std::fs::read_to_string("options.txt").is_ok_and(|s| {
            s.lines().any(|line| line.trim() == "lang:ru_ru")
        })
    }) {''')

# Extend launcher localization of text displayed on settings and home.
patch(catalog,
    '''        "Graphics preset" => "Профиль графики",''',
    '''        "Minecraft Java on Android Native" => "Minecraft Java на Android — нативно",
        "Native Java Edition • ARM64" => "Нативная Java Edition • ARM64",
        "Touch controls" => "Сенсорное управление",
        "Control layout" => "Расположение кнопок",
        "Android 16 dynamic theme" => "Динамическая тема Android 16",
        "Animations" => "Анимации",
        "Smooth" => "Плавно",
        "Installed worlds" => "Установленные миры",
        "Graphics preset" => "Профиль графики",''')
# Main hero headline: discoverable native Java-on-Android title, bilingual.
patch(pages,
    '''tr("Your Java worlds, on Android")''',
    '''tr("Minecraft Java on Android Native")''')
# Material 3 style animated interaction: press feedback alpha decays
# smoothly over 220 ms, with pill shape and accent-based highlight.
patch(pages,
    '''&& time.elapsed() < std::time::Duration::from_millis(160)''',
    '''&& time.elapsed() < std::time::Duration::from_millis(240)''')
patch(pages,
    '''                2.0,
                horizon_client::hud::rgba(255, 255, 255, 48),''',
    '''                (*h * 0.5).min(26.0),
                horizon_client::hud::rgba(
                    255, 255, 255,
                    (55.0 * (1.0 - time.elapsed().as_secs_f32() / 0.24).clamp(0.0, 1.0)) as u8,
                ),''')
# Animate active nav indicator using launcher uptime, but do not affect hitboxes
# or the main renderer. Existing Material You system accent is preserved.
patch(pages,
    '''        crate::documents::draw_ui(&mut ui);''',
    '''        crate::documents::draw_ui(&mut ui);''')

# Native Minecraft HUD glyphs as a visual signature in the launcher hero,
# while Material You Roboto remains for legible long Cyrillic paragraphs.
patch(pages,
    '''            if installing {
                let current = InstallStage::ALL''',
    '''            // Minecraft's own HUD atlas provides the pixel-game subtitle.
            ui.batch.text(
                &gui.atlas,
                "JAVA EDITION  /  ANDROID ARM64",
                32.0 * scale,
                (top + 80.0) * scale,
                horizon_client::hud::rgba(208, 188, 255, 255),
                true,
            );
            if installing {
                let current = InstallStage::ALL''')

# Fill remaining untranslated static native launcher guidance and status text.
extra_ru = {
    "Please keep Horizon open. Downloaded files are kept for retry.": "Не закрывайте Horizon. Загрузки сохраняются для повтора.",
    "01  Open a world or join a Java server": "01  Откройте мир или подключитесь к серверу Java",
    "02  Touch setup: Options > Controls": "02  Управление: Настройки > Управление",
    "03  Find packs and .hmod in the tabs": "03  Найдите ресурсы и .hmod во вкладках",
    "01  Download resources from Mojang": "01  Загрузка ресурсов Mojang",
    "02  Install and verify on this phone": "02  Установка и проверка на устройстве",
    "03  Play offline or sign in for servers": "03  Играйте офлайн или войдите для серверов",
    "Search Horizon mods or paste an HTTPS .hmod link": "Найдите моды Horizon или вставьте HTTPS-ссылку .hmod",
    "Horizon catalog / ZIP support is experimental": "Каталог Horizon и ZIP пока экспериментальные",
    "Verified downloads / enable in Installed": "Проверенные загрузки / включите в «Установлено»",
    "Open folder": "Открыть папку",
    "Import .hmod": "Импорт .hmod",
    "64-bit required": "Требуется 64-битная система",
    "Open in Files / Reports": "Открыть в файлах / отчётах",
    "Singleplayer / tap to enter server": "Одиночная игра / нажмите для ввода сервера",
    "Opened in Files. Return here after copying files.": "Открыты файлы. Вернитесь после копирования.",
    "Open the system Files app and choose Horizon Android.": "Откройте системные файлы и выберите Horizon Android.",
    "Repository opened in browser.": "Репозиторий открыт в браузере.",
    "No browser available to open the repository.": "Браузер для открытия репозитория не найден.",
    "No startup error. In game: F3 shows device, terrain and frame diagnostics.": "Ошибок запуска нет. В игре F3 показывает диагностику устройства и FPS.",
    "Recording starts on Play. Detailed timings add overhead. Return here to save the report.": "Запись начинается при запуске. Подробная диагностика снижает FPS.",
    "Performance recording off.": "Запись производительности выключена.",
    "Reports opened in Files. Copy or share a report from there.": "Отчёты открыты в файлах. Их можно скопировать.",
    "Mouse mode uses a physical keyboard. Touch mode keeps the Android keyboard.": "Режим мыши требует клавиатуру. Сенсорный режим использует клавиатуру Android.",
    "Applies to the launcher and game. Does not change touch bindings.": "Применяется к лаунчеру и игре. Кнопки управления не меняются.",
    "Uses the system GPU driver. Applies on the next game launch.": "Используется системный драйвер GPU. Применится при следующем запуске.",
    "For older GPUs. Requires ES 3.0+ and sufficient driver limits.": "Для старых GPU. Нужен OpenGL ES 3.0+.",
    "Groups terrain draws and enables supported GPU culling.": "Группирует отрисовку чанков и отсечение на GPU.",
    "Direct terrain draws for drivers with missing or transparent blocks.": "Прямая отрисовка для драйверов с пропадающими блоками.",
    "Each profile keeps its own game settings and saves.": "У каждого профиля отдельные настройки и миры.",
    "Deletes only the selected file from this profile. This cannot be undone.": "Удаляет выбранный файл без возможности восстановления.",
}
p=ROOT/catalog
src=p.read_text(encoding="utf-8")
anchor='        "Minecraft Java on Android Native" => "Minecraft Java на Android — нативно",'
assert src.count(anchor)==1
entries=''.join('        '+repr(en).replace("'",'"')+' => '+repr(ru).replace("'",'"')+',\n' for en,ru in extra_ru.items())
p.write_text(src.replace(anchor,entries+anchor,1),encoding="utf-8")
for path in (pages,"crates/horizon-client/src/android/chooser.rs"):
    p=ROOT/path
    src=p.read_text(encoding="utf-8")
    for en in extra_ru:
        old='"'+en+'"'
        if old in src:
            src=src.replace(old,'tr("'+en+'")')
    p.write_text(src,encoding="utf-8")

# Version identifiers distinguish this stable candidate from upstream 0.7.3.
patch("packaging/android/build.gradle", "versionCode 24", "versionCode 25")
patch("packaging/android/build.gradle", "versionName '0.7.3'", "versionName '1.0.0'")

print("Release polish: native finger shortcut, editor localization, search heading, animated Material press feedback.")
