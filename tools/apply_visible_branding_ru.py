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
     '&format!("HorizonCraft {}", crate::backend::VERSION)'),
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
p.write_text(s,encoding="utf-8")

# The online catalog's provider names and URLs are preserved intentionally:
# hiding actual download provenance would be misleading and break trust.
catalog=root/"crates/horizon-client/src/android/catalog.rs"
s=catalog.read_text(encoding="utf-8")
s=s.replace('No Horizon shader packs match this search.', 'Нет подходящих пакетов шейдеров.')
catalog.write_text(s,encoding="utf-8")
print("Visible launcher branded HorizonCraft; native touch settings translated to Russian.")
