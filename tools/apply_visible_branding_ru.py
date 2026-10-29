#!/usr/bin/env python3
"""Visible product branding and Russian UI labels; preserve source licenses.

Applies after graphics, touch and page overlays. Never rewrites dependency
identifiers, asset formats, service endpoints, security or license metadata.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
def rewrite(path, replacements):
    p=root/path
    s=p.read_text(encoding="utf-8")
    for before, after in replacements:
        n=s.count(before)
        if n != 1:
            raise RuntimeError(f"{path}: missing/ambiguous localization anchor ({n}) {before[:96]!r}")
        s=s.replace(before,after,1)
    p.write_text(s,encoding="utf-8")

# These are ACTUAL Minecraft Options screen titles and controls, not fake
# launcher tabs. Do not alter the option identifiers or serialized settings.
options="crates/horizon-client/src/options_ui.rs"
rewrite(options,[
    ('Page::Touch => "Touch Controls",','Page::Touch => "Сенсорное управление",'),
    ('Page::Controller => "Controller Settings",','Page::Controller => "Настройки геймпада",'),
    ('Page::PadBinds => "Controller Binds",','Page::PadBinds => "Кнопки геймпада",'),
    ('Page::Extras => "Horizon Extras",','Page::Extras => "Дополнительные настройки",'),
    ('Page::Horizon => "Horizon Settings",','Page::Horizon => "Настройки игры",'),
    ('Page::Agent => "AI Agent",','Page::Agent => "ИИ-помощник",'),
    ('Page::Mods => "Mods",','Page::Mods => "Моды",'),
    ('Page::NativeMod(_) => "Mod Settings",','Page::NativeMod(_) => "Настройки мода",'),
    ('Page::ShaderPacks => "Shader Packs",','Page::ShaderPacks => "Шейдеры",'),
    ('Opt::AndroidInputMode => "Input device",','Opt::AndroidInputMode => "Устройство ввода",'),
    ('Text::literal("Customize layout...")','Text::literal("Настроить кнопки...")'),

    ('Opt::TouchMode => "Control scheme",','Opt::TouchMode => "Схема управления",'),
    ('Opt::TouchAnalog => "360-degree movement",','Opt::TouchAnalog => "Свободное движение 360°",'),
    ('Opt::TouchCircleSize => "Touch circle size",','Opt::TouchCircleSize => "Размер сенсорного джойстика",'),
    ('Opt::TouchAttackSide => "Attack indicator side",','Opt::TouchAttackSide => "Расположение кнопки атаки",'),
    ('Opt::TouchHorizontalMargin => "HUD margins: left / right",','Opt::TouchHorizontalMargin => "Отступы слева и справа",'),
    ('Opt::TouchVerticalMargin => "HUD margins: top / bottom",','Opt::TouchVerticalMargin => "Отступы сверху и снизу",'),
    ('Opt::TouchButtonScale => "Control button size",','Opt::TouchButtonScale => "Размер сенсорных кнопок",'),
    ('Opt::TouchInteract => "Interact button",','Opt::TouchInteract => "Кнопка взаимодействия",'),
    ('Opt::TouchLeftHand => "Left handed",','Opt::TouchLeftHand => "Для левшей",'),
    ('Opt::TouchSprintButton => "Sprint button",','Opt::TouchSprintButton => "Кнопка бега",'),
    ('Opt::TouchSprintToggle => "Toggle sprint button",','Opt::TouchSprintToggle => "Переключатель бега",'),
    ('Opt::TouchInventoryControls => "Controls in inventory",','Opt::TouchInventoryControls => "Управление в инвентаре",'),
    ('Opt::TouchSwapJumpSneak => "Swap jump / sneak",','Opt::TouchSwapJumpSneak => "Поменять прыжок и приседание",'),
    ('Opt::TouchAutoSprint => "Auto Sprint",','Opt::TouchAutoSprint => "Автоматический бег",'),
])

# Visible native launcher name. Keep application ID / JNI class intact so an
# APK signed with the same certificate installs over the previous version.
pages="crates/horizon-client/src/android/launcher_pages.rs"
rewrite(pages,[
    ('&format!("Horizon Android {}", crate::backend::VERSION)',
     '"HorizonCraft 1.3.3"'),
])
p=root/pages
s=p.read_text(encoding="utf-8")
# Translate textual labels without changing the online providers, their API
# identifiers or the legal credits screen.
s=s.replace('"Horizon Mods"', '"Моды онлайн"')
s=s.replace('"Horizon native .hshader packs"', '"Совместимые пакеты шейдеров"')
s=s.replace('"Modrinth shader ZIPs / experimental compatibility; some packs may not work"',
            '"Онлайн-шейдеры ZIP / совместимость не гарантируется"')
s=s.replace('"Search Horizon mods or paste an HTTPS .hmod link"',
            '"Поиск модов или импорт HTTPS-ссылки .hmod"')
# Russian text for the screenshot's actual home-card steps and catalog.
s=s.replace('Minecraft 26.3  /  Profile {}', 'Minecraft 26.3  /  Профиль {}')
s=s.replace('Online catalog  /  Page {}  /  {} results',
            'Онлайн-каталог  /  Страница {}  /  {} результатов')
s=s.replace('"Repository opened in browser."', '"Страница проекта открыта."')
s=s.replace('"No browser available to open the repository."',
            '"Браузер для открытия проекта не найден."')
p.write_text(s,encoding="utf-8")

# Home card passes unnumbered strings through tr(), whereas older localization
# keys contained the prefix "01  ". Keep both forms so no English leaks into
# the new functional home layout.
catalog=root/"crates/horizon-client/src/android/catalog.rs"
s=catalog.read_text(encoding="utf-8")
anchor='        "On" => "Вкл.",'
if s.count(anchor)!=1: raise RuntimeError("Missing Russian catalog lookup anchor")
extra=[
    ("Open a world or join a Java server", "Откройте мир или подключитесь к серверу Java"),
    ("Touch setup: Options > Controls", "Управление: Настройки → Управление"),
    ("Find packs and .hmod in the tabs", "Моды и ресурсы доступны во вкладках"),
    ("Download resources from Mojang", "Скачивание игровых ресурсов"),
    ("Install and verify on this phone", "Установка и проверка на устройстве"),
    ("Play offline or sign in for servers", "Играйте офлайн или войдите для серверов"),
]
new=''.join(f'        "{en}" => "{ru}",\\n' for en,ru in extra)
# replace escaped newline sequences with source-code newlines
new=new.replace('\\n','\n')
catalog.write_text(s.replace(anchor,new+anchor,1),encoding="utf-8")

# Android native window caption and clipboard item label.
rewrite("crates/horizon-client/src/android/launcher.rs", [
    ('with_title("Horizon Android")', 'with_title("HorizonCraft")')
])
rewrite("crates/horizon-client/src/android/platform.rs", [
    ('env.new_string("Horizon")?', 'env.new_string("HorizonCraft")?')
])

# GitHub button opens this app's official repository, not the engine source.
rewrite("crates/horizon-client/src/android/platform.rs", [
    ('open_url("https://github.com/Vasysik/horizon-android")',
     'open_url("https://github.com/Vanich-Chat-GPT/Horizon-Android-By-Vanich")')
])

# The online catalog's provider names and URLs are preserved intentionally:
# hiding actual download provenance would be misleading and break trust.
catalog=root/"crates/horizon-client/src/android/catalog.rs"
s=catalog.read_text(encoding="utf-8")
s=s.replace('No Horizon shader packs match this search.', 'Нет подходящих пакетов шейдеров.')
catalog.write_text(s,encoding="utf-8")
print("Visible launcher branded HorizonCraft; native touch settings translated to Russian.")
