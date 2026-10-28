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
patch(display, "[100, 85, 75, 67, 50, 25]", "[100, 90, 85, 75, 67, 60, 50, 40]")
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
      '        (h * 0.5).min(26.0),\n        if accent { color::ACCENT } else { color::RAISED },')
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
patch(theme, 'pub const DARK: Palette = Palette {\n    page: 0x0d0e13,',
      'pub const DARK: Palette = Palette {\n    page: 0x141218,')
patch(theme, '    plate_soft: 0x181a22,', '    plate_soft: 0x211f26,')
patch(theme, '    plate: 0x20222c,', '    plate: 0x29262f,')
patch(theme, '    surface: 0x16181f,', '    surface: 0x2b2930,')
patch(theme, '    rule: 0x24262f,', '    rule: 0x49454f,')
patch(theme, '    ink: 0xecedf3,', '    ink: 0xe6e0e9,')
patch(theme, '    ink_soft: 0xc5c7d1,', '    ink_soft: 0xcac4d0,')
patch(theme, '    muted: 0x8b8f9c,', '    muted: 0x938f99,')
patch(theme, '    accent: 0x9a86ff,', '    accent: 0xd0bcff,')
patch(theme, '    on_accent: 0x0d0e13,', '    on_accent: 0x381e72,')
print("Horizon Android overlay applied successfully.")
