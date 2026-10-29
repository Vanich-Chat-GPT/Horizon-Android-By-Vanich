#!/usr/bin/env python3
"""Apply the Vanich Android UI overlay to upstream Horizon Android sources.

Strict replacements deliberately fail when upstream changes so a CI build cannot
silently skip requested features.
"""
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

def patch(path, old, new):
    p = ROOT / path
    source = p.read_text(encoding="utf-8")
    if old not in source:
        raise RuntimeError(f"{path}: missing expected source snippet: {old[:100]!r}")
    p.write_text(source.replace(old, new, 1), encoding="utf-8")

# Actual native Android render surface scale (not a mock UI slider).
display = "crates/horizon-client/src/android/display.rs"
patch(display, "pub const PRESETS: [u32; 6] = [100, 85, 75, 67, 50, 25];", "pub const PRESETS: [u32; 8] = [100, 90, 85, 75, 67, 60, 50, 40];")
patch(display, "Self(percent.clamp(25, 100))", "Self(percent.clamp(40, 100))")
patch(display, "Enter a whole percentage from 25 to 100", "Enter a whole percentage from 40 to 100")
patch(display, "if !(25..=100).contains(&percent)", "if !(40..=100).contains(&percent)")
patch(display, "Enter a percentage from 25 to 100", "Enter a percentage from 40 to 100")
patch(display, "self.0.clamp(25, 100)", "self.0.clamp(40, 100)")
# Change test expectations to reflect the new 40% minimum.
patch(display, 'RenderScale::new(25).buffer_size([480, 854]), [320, 569]', 'RenderScale::new(40).buffer_size([480, 854]), [320, 569]')
patch(display, 'RenderScale::new(25).buffer_size([240, 320]), [240, 320]', 'RenderScale::new(40).buffer_size([240, 320]), [240, 320]')
patch(display, 'RenderScale::new(25).buffer_size([0, 0]), [1, 1]', 'RenderScale::new(40).buffer_size([0, 0]), [1, 1]')
patch(display, '            25\n        );', '            40\n        );')

# Android launcher localization, persisted per installation and toggled from Settings.
catalog = "crates/horizon-client/src/android/catalog.rs"
patch(catalog, '/// Temporary dev registration published as Minecraft Nintendo Switch by PrismarineJS.', r'''
/// Launcher strings only; Minecraft world and menus use vanilla language settings.
static RUSSIAN: std::sync::atomic::AtomicBool =
    std::sync::atomic::AtomicBool::new(true);

pub fn tr(text: &str) -> &str {
    if !RUSSIAN.load(std::sync::atomic::Ordering::Relaxed) {
        return text;
    }
    match text {
        "Play" => "Играть",
        "Mods" => "Моды",
        "Packs" => "Ресурсы",
        "Shaders" => "Шейдеры",
        "Installed" | "Files" => "Установлено",
        "Settings" | "Setup" => "Настройки",
        "Rendering" => "Рендеринг",
        "Client resolution" => "Масштаб 3D",
        "Profile" => "Профиль",
        "Orientation" => "Ориентация",
        "Input" => "Управление",
        "Performance recording" => "Запись FPS",
        "Performance report" => "Отчёт о FPS",
        "Server" => "Сервер",
        "Language" => "Язык",
        "Russian" => "Русский",
        "English" => "English",
        "Launch settings" => "Настройки запуска",
        "Getting your game ready" => "Подготовка игры",
        "Ready to play" => "Готово к игре",
        "Your Java worlds" => "Ваши миры Java",
        "Your Java worlds, on Android" => "Миры Minecraft Java на Android",
        "Retry installation" => "Повторить загрузку",
        "Download Minecraft 26.3" => "Скачать Minecraft 26.3",
        "Search" => "Поиск",
        "Import" => "Импорт",
        "Import file" => "Добавить файл",
        "Remove" => "Удалить",
        "Previous" => "Назад",
        "Next" => "Далее",
        "Microsoft / Xbox account" => "Аккаунт Microsoft / Xbox",
        "Startup diagnostics" => "Диагностика запуска",
        "Horizon Mods" => "Моды Horizon",
        "Shader Packs" => "Пакеты шейдеров",
        "Resource Packs" => "Наборы ресурсов",
        "Native resolution" => "Исходное разрешение",
        "Lower resolution for the whole picture" => "Меньшее разрешение изображения",
        "Custom percentage..." => "Свой процент...",
        "Small screens retain a usable menu size." => "Меню остаётся читаемым на маленьких экранах.",
        "Input mode" => "Режим ввода",
        "Rendering mode" => "Режим рендеринга",
        "Screen orientation" => "Ориентация экрана",
        "Choose profile" => "Выбрать профиль",
        "Default profile" => "Основной профиль",
        "Create profile" => "Создать профиль",
        "Separate saves, mods and packs" => "Отдельные миры, моды и ресурсы",
        "Remove add-on?" => "Удалить дополнение?",
        "Cancel" => "Отмена",
        "Vulkan / GPU batching" => "Vulkan / ускорение GPU",
        "Vulkan / compatibility" => "Vulkan / совместимость",
        "OpenGL ES / experimental" => "OpenGL ES / экспериментально",
        "Automatic" => "Автоматически",
        "Touch Controls" => "Сенсорное управление",
        "Touch controls" => "Сенсорное управление",
        "Touch & Android keyboard" => "Касания и клавиатура Android",
        "Keyboard & mouse" => "Клавиатура и мышь",
        "Landscape (sensor)" => "Альбомная (датчик)",
        "Portrait (sensor)" => "Портретная (датчик)",
        "Landscape (reversed)" => "Альбомная (обратная)",
        "Portrait (reversed)" => "Портретная (обратная)",
        "Automatic rotation" => "Автоповорот",
        "On" => "Вкл.",
        "Off" => "Выкл.",
        _ => text,
    }
}

/// Temporary dev registration published as Minecraft Nintendo Switch by PrismarineJS.''')
patch(catalog, '    pub profile: u32,\n', '    pub profile: u32,\n    pub russian: bool,\n')
patch(catalog, '    pub fn load(home: &Path) -> Self {\n', '    pub fn load(home: &Path) -> Self {\n')
patch(catalog, '        config.microsoft_client_id = MICROSOFT_CLIENT_ID.into();',
      '''        config.microsoft_client_id = MICROSOFT_CLIENT_ID.into();
        // Old installations default to Russian; selecting English persists.
        config.russian = value.get("russian").and_then(|v| v.as_bool()).unwrap_or(true);
        RUSSIAN.store(config.russian, std::sync::atomic::Ordering::Relaxed);''')
patch(catalog, '            Self::Play => "Play",', '            Self::Play => tr("Play"),')
for en in ("Mods", "Packs", "Shaders", "Installed", "Settings"):
    patch(catalog, f'            Self::{en} => "{en}",', f'            Self::{en} => tr("{en}"),')

pages = "crates/horizon-client/src/android/launcher_pages.rs"
patch(pages, 'use super::*;', 'use super::*;\nuse crate::catalog::tr;')
patch(pages, '    RecordPerformance,\n', '    RecordPerformance,\n    Language,\n')
# Style uses rounded Material-inspired filled/pill buttons, with the same hit targets.
patch(pages, '        2.0,\n        if accent { color::ACCENT } else { color::RAISED },',
      '        2.0,\n        if accent { color::ACCENT } else { color::RAISED },')
patch(pages, '    let label = ui.fit_text(Face::Medium, font, label, w - 2.0 * padding);',
      '    let label = ui.fit_text(Face::Medium, font, tr(label), w - 2.0 * padding);')
# Localize fixed page headlines and launcher-visible labels.
for en in ("Getting your game ready", "Ready to play", "Your Java worlds",
           "Your Java worlds, on Android", "Retry installation", "Download Minecraft 26.3",
           "Horizon Mods", "Shader Packs", "Resource Packs", "Launch settings"):
    patch(pages, f'"{en}"', f'tr("{en}")')
patch(pages, '                if w < 700.0 {\n                    match page {', '                if w < 700.0 {\n                    match page {')
patch(pages, '                        Page::Installed => "Files",', '                        Page::Installed => tr("Files"),')
patch(pages, '                        Page::Settings => "Setup",', '                        Page::Settings => tr("Setup"),')
patch(pages, '                    "On / up to 30 min"', '                    "On / up to 30 min"')
patch(pages, '                ("Rendering", c.renderer.label().to_owned(), Action::Renderer),',
      '                (tr("Rendering"), c.renderer.label().to_owned(), Action::Renderer),')
for en in ("Client resolution", "Orientation", "Performance recording",
           "Performance report", "Server"):
    patch(pages, f'"{en}"', f'tr("{en}")')
patch(pages, '("Profile", format!("Profile {}", c.profile), Action::Profile)',
      '(tr("Profile"), format!("Profile {}", c.profile), Action::Profile)')
patch(pages, '("Input", c.input_host.label().to_owned(), Action::InputHost)',
      '(tr("Input"), c.input_host.label().to_owned(), Action::InputHost)')
patch(pages, '                (\n                    tr("Server"),', '''                (
                    tr("Language"),
                    (if c.russian { tr("Russian") } else { tr("English") }).into(),
                    Action::Language,
                ),
                (
                    tr("Server"),''')
patch(pages, '8.0 * row_height', '9.0 * row_height')
patch(pages, '8.0 * row_height', '9.0 * row_height')
patch(pages, '            Some(Action::Profile) => self.open_chooser(chooser::Kind::Profile),',
      '''            Some(Action::Language) => {
                self.catalog.config.russian = !self.catalog.config.russian;
                crate::catalog::set_language(self.catalog.config.russian);
                self.catalog.config.save(&self.home)?;
            }
            Some(Action::Profile) => self.open_chooser(chooser::Kind::Profile),''')
patch(catalog, 'pub fn tr(text: &str) -> &str {',
      '''pub fn set_language(russian: bool) {
    RUSSIAN.store(russian, std::sync::atomic::Ordering::Relaxed);
}
pub fn tr(text: &str) -> &str {''')

# Android's system dynamic colors are usable by Java UI; this Rust-rendered
# launcher uses Android 16 Material You inspired fallback colors and geometry.
styles = "packaging/android/res/values/styles.xml"
patch(styles, '#9a86ff', '#D0BCFF')
theme = "crates/horizon-theme/src/lib.rs"
# Prefer the device's licensed system Roboto (Cyrillic coverage + Material type).
# The once-cell owns the bytes for the lifetime of the process, avoiding per-frame
# allocations and bundling redistributed font binaries.
ui_theme = "crates/horizon-client/src/ui_theme.rs"
patch(ui_theme, '''        Self {
            faces: [
                f(horizon_theme::fonts::GEIST_REGULAR),
                f(horizon_theme::fonts::GEIST_MEDIUM),
            ],
        }''', '''        #[cfg(target_os = "android")]
        fn android_roboto() -> Option<FontRef<'static>> {
            static FONT_BYTES: std::sync::OnceLock<Option<Vec<u8>>> =
                std::sync::OnceLock::new();
            FONT_BYTES.get_or_init(|| {
                [
                    "/system/fonts/Roboto-Regular.ttf",
                    "/system/fonts/RobotoStatic-Regular.ttf",
                    "/system/fonts/NotoSans-Regular.ttf",
                ]
                .into_iter()
                .find_map(|path| {
                    let data = std::fs::read(path).ok()?;
                    let font = FontRef::try_from_slice(&data).ok()?;
                    // Prevent Cyrillic labels from turning into empty glyphs.
                    (font.glyph_id('Ж').0 != 0).then_some(data)
                })
            }).as_deref().and_then(|bytes| FontRef::try_from_slice(bytes).ok())
        }
        #[cfg(target_os = "android")]
        let faces = [
            android_roboto().unwrap_or_else(|| f(horizon_theme::fonts::GEIST_REGULAR)),
            android_roboto().unwrap_or_else(|| f(horizon_theme::fonts::GEIST_MEDIUM)),
        ];
        #[cfg(not(target_os = "android"))]
        let faces = [
            f(horizon_theme::fonts::GEIST_REGULAR),
            f(horizon_theme::fonts::GEIST_MEDIUM),
        ];
        Self { faces }''')

# Translate the native popover choices as well as the main settings page.
chooser = "crates/horizon-client/src/android/chooser.rs"
patch(chooser, 'use crate::catalog::RendererMode;',
      'use crate::catalog::{RendererMode, tr};')
patch(chooser, '        self.chooser = Some(Chooser {\n            title,\n            help,\n            choices,',
      '''        let choices = choices.into_iter().map(|(name, detail, action, selected)| (
            tr(&name).to_owned(), tr(&detail).to_owned(), action, selected
        )).collect();
        self.chooser = Some(Chooser {
            title: tr(title),
            help: tr(help),
            choices,''')
patch(chooser, '"Enter a value from 25 to 100"', '"Enter a value from 40 to 100"')
patch(chooser, '"Native resolution"', 'tr("Native resolution")')
patch(chooser, '"Lower resolution for the whole picture"', 'tr("Lower resolution for the whole picture")')
patch(chooser, '"Custom percentage...".into()', 'tr("Custom percentage...").into()')
patch(chooser, '"Client resolution",\n                    "Small screens retain a usable menu size.",',
      'tr("Client resolution"),\n                    tr("Small screens retain a usable menu size."),')


# Fixed violet launcher accent; no Material You wallpaper color lookup.
patch("crates/horizon-client/src/ui_theme.rs",
      '    pub const ACCENT: u32 = hex(P.accent, 255);',
      '''    pub const ACCENT: u32 = hex(P.accent, 255);
    pub fn launcher_accent() -> u32 { hex(0x9690ff, 255) }''')
for path in ("crates/horizon-client/src/android/launcher_pages.rs",
             "crates/horizon-client/src/android/chooser.rs",
             "crates/horizon-client/src/android/login.rs"):
    file = ROOT / path
    source = file.read_text(encoding="utf-8")
    file.write_text(source.replace("color::ACCENT", "color::launcher_accent()"), encoding="utf-8")

# Real device-oriented graphics profiles, backed by Minecraft options.txt and
# the native render surface. Changing a profile never occurs silently at launch.
patch(catalog, '#[derive(Clone, Default, Serialize, Deserialize)]\n#[serde(default)]\npub struct Config {',
      '''#[derive(Clone, Copy, Default, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum QualityPreset {
    Eco,
    #[default]
    Balanced,
    Quality,
}
impl QualityPreset {
    pub fn next(self) -> Self {
        match self { Self::Eco => Self::Balanced, Self::Balanced => Self::Quality, Self::Quality => Self::Eco }
    }
    pub fn label(self) -> &'static str {
        match self { Self::Eco => "Economy", Self::Balanced => "Balanced", Self::Quality => "Quality" }
    }
}

#[derive(Clone, Default, Serialize, Deserialize)]
#[serde(default)]
pub struct Config {''')
patch(catalog, '    pub russian: bool,\n', '    pub russian: bool,\n    pub quality_preset: QualityPreset,\n')
patch(catalog, '        "Rendering" => "Рендеринг",',
      '''        "Graphics preset" => "Профиль графики",
        "Economy" => "Экономия",
        "Balanced" => "Баланс",
        "Quality" => "Качество",
        "Rendering" => "Рендеринг",''')
patch(pages, '    Language,\n', '    Language,\n    GraphicsPreset,\n')
patch(pages, '                (tr("Rendering"), c.renderer.label().to_owned(), Action::Renderer),',
      '''                (tr("Graphics preset"), tr(c.quality_preset.label()).into(), Action::GraphicsPreset),
                (tr("Rendering"), c.renderer.label().to_owned(), Action::Renderer),''')
patch(pages, '9.0 * row_height', '10.0 * row_height')
patch(pages, '9.0 * row_height', '10.0 * row_height')
patch(pages, '            Some(Action::Language) => {',
      '''            Some(Action::GraphicsPreset) => {
                use crate::catalog::QualityPreset;
                let next = self.catalog.config.quality_preset.next();
                self.catalog.config.quality_preset = next;
                let (scale, chunks, simulation, max_fps, fancy) = match next {
                    QualityPreset::Eco => (50, 6, 5, 60, false),
                    QualityPreset::Balanced => (75, 9, 7, 60, false),
                    QualityPreset::Quality => (100, 14, 10, 90, true),
                };
                let resolution = crate::display::RenderScale::new(scale);
                self.catalog.config.render_scale = resolution;
                crate::display::set_scale(resolution);
                let path = self.catalog.config.game_home(&self.home).join("options.txt");
                let mut settings = horizon_client::settings::Settings::load(&path);
                settings.render_distance = chunks;
                settings.simulation_distance = simulation;
                settings.max_fps = max_fps;
                settings.vsync = !fancy;
                settings.graphics_preset = if fancy { "fancy" } else { "fast" }.into();
                settings.clouds = if fancy { "true" } else { "false" }.into();
                settings.particles = if fancy { 0 } else { 2 };
                settings.entity_shadows = fancy;
                settings.smooth_lighting = fancy;
                settings.mipmap_levels = if fancy { 4 } else { 0 };
                settings.biome_blend = if fancy { 2 } else { 0 };
                settings.save(&path);
                self.catalog.config.save(&self.home)?;
                self.catalog.status = tr("Graphics profile saved. Applies when Play starts.").into();
            }
            Some(Action::Language) => {''')
patch(catalog, '        "Graphics preset" => "Профиль графики",',
      '''        "Graphics profile saved. Applies when Play starts." => "Профиль сохранён. Изменения применятся при запуске.",
        "Graphics preset" => "Профиль графики",''')


# Keep the game itself in the same language as the Android launcher. Horizon's
# own language resources are still loaded through its standard Mojang pipeline.
patch(pages, '''            Some(Action::Language) => {
                self.catalog.config.russian = !self.catalog.config.russian;
                crate::catalog::set_language(self.catalog.config.russian);
                self.catalog.config.save(&self.home)?;
            }''', '''            Some(Action::Language) => {
                self.catalog.config.russian = !self.catalog.config.russian;
                crate::catalog::set_language(self.catalog.config.russian);
                let path = self.catalog.config.game_home(&self.home).join("options.txt");
                let mut settings = horizon_client::settings::Settings::load(&path);
                settings.language = if self.catalog.config.russian { "ru_ru" } else { "en_us" }.into();
                settings.save(&path);
                self.catalog.config.save(&self.home)?;
            }''')


# Android 13–16 supports Material themed launcher icons when the adaptive icon
# declares a monochrome layer. Keep the upstream artwork as foreground.
manifest = "packaging/android/AndroidManifest.xml"
patch(manifest, 'android:icon="@drawable/launcher_icon"',
      'android:icon="@mipmap/ic_launcher"')
res = ROOT / "packaging/android/res"
(res / "mipmap-anydpi-v26").mkdir(parents=True, exist_ok=True)
(res / "mipmap-anydpi-v26/ic_launcher.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/horizon_icon_background"/>
    <foreground android:drawable="@drawable/launcher_icon"/>
    <monochrome android:drawable="@drawable/ic_launcher_monochrome"/>
</adaptive-icon>
""", encoding="utf-8")
(res / "values/horizon_icon_colors.xml").write_text("""<resources>
    <color name="horizon_icon_background">#141218</color>
</resources>
""", encoding="utf-8")
(res / "drawable/ic_launcher_monochrome.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#FFFFFFFF"
        android:pathData="M54,14 L87,33 L87,74 L54,93 L21,74 L21,33 Z"/>
    <path android:fillColor="#FF141218"
        android:pathData="M54,32 L70,41 L70,65 L54,74 L38,65 L38,41 Z"/>
    <path android:fillColor="#FFFFFFFF"
        android:pathData="M54,38 L65,44 L54,50 L43,44 Z M42,50 L51,55 L51,68 L42,63 Z M57,55 L66,50 L66,63 L57,68 Z"/>
</vector>
""", encoding="utf-8")


# Localize native account screen labels, without altering authentication
# protocol messages or account/token handling.
login = "crates/horizon-client/src/android/login.rs"
patch(login, 'use super::pages::{Action, button};',
      'use super::pages::{Action, button};\nuse crate::catalog::tr;')
patch(login, 'format!("Signed in: {name}")',
      'format!("{}: {name}", tr("Signed in"))')
patch(login, 'format!("Sign in required: {name}")',
      'format!("{}: {name}", tr("Sign in required"))')
patch(login, '"Signing in...".into()', 'tr("Signing in...").into()')
patch(login, 'format!("Offline: {offline_name}")',
      'format!("{}: {offline_name}", tr("Offline"))')
patch(login, '"Offline / Sign in".into()', 'tr("Offline / Sign in").into()')
for text in (
    "Offline player name",
    "Used when signed out of Microsoft.",
    "Accounts",
    "Account saved securely. Sessions renew automatically.",
    "Your password is entered in Microsoft's browser.",
    "Requesting a sign-in code...",
):
    patch(login, f'"{text}"', f'tr("{text}")')
patch(login, '"Offline player name"', 'tr("Offline player name")')
for en, ru in (
    ("Signed in", "Выполнен вход"),
    ("Sign in required", "Требуется вход"),
    ("Signing in...", "Выполняется вход..."),
    ("Offline", "Офлайн"),
    ("Offline / Sign in", "Офлайн / Войти"),
    ("Offline player name", "Имя игрока офлайн"),
    ("Used when signed out of Microsoft.", "Используется без аккаунта Microsoft."),
    ("Accounts", "Аккаунты"),
    ("Account saved securely. Sessions renew automatically.", "Аккаунт сохранён. Вход обновляется автоматически."),
    ("Your password is entered in Microsoft's browser.", "Пароль вводится только в браузере Microsoft."),
    ("Requesting a sign-in code...", "Запрос кода входа..."),
    ("Done", "Готово"),
    ("Copy code", "Копировать код"),
    ("Enter an offline name", "Введите имя игрока"),
    ("Request Minecraft API approval", "Запросить доступ Minecraft API"),
    ("Copy code and open browser", "Копировать код и открыть браузер"),
    ("Restart browser sign-in", "Повторить вход через браузер"),
    ("Switch Microsoft account", "Сменить аккаунт Microsoft"),
    ("Sign in with browser", "Войти через браузер"),
    ("Use a device code instead", "Войти через код устройства"),
    ("Cancel sign-in", "Отменить вход"),
    ("Sign out", "Выйти"),
    ("Close", "Закрыть"),
    ("Back (sign-in continues)", "Назад (вход продолжается)"),
):
    patch(catalog, '        "On" => "Вкл.",',
          f'        "{en}" => "{ru}",\n        "On" => "Вкл.",')


# Install RU game-menu defaults on a fresh game profile, but never overwrite
# options.txt (and the player's language choice) on an existing installation.
patch("crates/horizon-client/src/android/launcher.rs",
      '        if horizon_client::official_install::ready(&self.home) {',
      '''        if horizon_client::official_install::ready(&self.home) {
            let options_path = self.catalog.config.game_home(&self.home).join("options.txt");
            if !options_path.exists() {
                let mut initial = horizon_client::settings::Settings::load(&options_path);
                initial.language = if self.catalog.config.russian { "ru_ru" } else { "en_us" }.into();
                initial.save(&options_path);
            }''')

# Pin the exact Mojang 26.3 manifest the Horizon engine is built against.
# Mojang can republish version metadata; an unpinned latest manifest triggers
# Horizon's built-in integrity gate even when game JAR hashes match.
preparer = "tools/android_prepare.py"
patch(preparer, "    lab.download(entry['url'], manifest_path, entry['sha1'])",
      """    pinned_sha1 = "11f1aefe473eefba0af62e3286c33b692807b2eb"
    pinned_url = f"https://piston-meta.mojang.com/v1/packages/{pinned_sha1}/{version}.json"
    lab.download(pinned_url, manifest_path, pinned_sha1)""")

print("Horizon Android overlay applied successfully.")
