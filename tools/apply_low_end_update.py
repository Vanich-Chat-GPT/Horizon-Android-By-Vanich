#!/usr/bin/env python3
"""v1.1.0 Low End: conservative Android-only frame budget and Minecraft-style launcher.
Applied after the v1.0.0 overlay, touch and release-polish patches.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

def replace(path, old, new):
    file = root / path
    data = file.read_text(encoding="utf-8")
    if data.count(old) != 1:
        raise RuntimeError(f"{path}: expected one anchor, found {data.count(old)}: {old[:90]!r}")
    file.write_text(data.replace(old, new, 1), encoding="utf-8")

pages = "crates/horizon-client/src/android/launcher_pages.rs"
catalog = "crates/horizon-client/src/android/catalog.rs"
streaming = "crates/horizon-client/src/streaming.rs"

# Lower-end profile: bound the expensive view/simulation radius and reduce
# GPU render target area. No claims of a guaranteed FPS or RAM percentage.
replace(pages, "QualityPreset::Eco => (50, 5, 5, 60, false),",
        "QualityPreset::Eco => (50, 4, 4, 60, false),")
replace(pages, "QualityPreset::Balanced => (67, 8, 6, 90, false),",
        "QualityPreset::Balanced => (67, 7, 5, 90, false),")
replace(pages, "settings.entity_distance = if fancy { 1.0 } else { 0.65 };",
        "settings.entity_distance = if fancy { 1.0 } else if matches!(next, QualityPreset::Eco) { 0.5 } else { 0.65 };")
replace(pages, "settings.weather_radius = if fancy { 8 } else { 4 };",
        "settings.weather_radius = if fancy { 8 } else if matches!(next, QualityPreset::Eco) { 2 } else { 4 };")

# A stricter frame-time budget on Android; the receiver retains queued
# results instead of discarding them. This may delay chunk appearance.
replace(streaming, "let received = received.take(48).collect::<Vec<_>>();",
        "let received = received.take(24).collect::<Vec<_>>();")

# Minecraft-inspired square-cut bevel + Material You dynamic accent. Retain
# accessible touch hit targets and existing Roboto Cyrillic text rendering.
replace(pages, '''        (h * 0.5).min(26.0),
        if accent { color::ACCENT } else { color::RAISED },
    );
    let padding = (w * 0.12).clamp(4.0, 12.0);''',
    '''        4.0,
        if accent { color::ACCENT } else { color::RAISED },
    );
    // Pixel-game bevel: subtle top highlight and bottom shadow. Dynamic
    // Material You accent is still supplied by the launcher color palette.
    ui.rounded(x + 2.0, y + 2.0, (w - 4.0).max(0.0), 2.0, 0.0, color::HOVER);
    ui.rounded(x + 2.0, y + h - 4.0, (w - 4.0).max(0.0), 2.0, 0.0, color::BG);
    let padding = (w * 0.12).clamp(4.0, 12.0);''')

# Make the home headline distinguish the update without changing Minecraft
# gameplay strings or loading third-party game art.
replace(pages, 'tr("Minecraft Java on Android Native")',
        'tr("Minecraft Java on Android Native")')
replace(pages, '"JAVA EDITION  /  ANDROID ARM64",',
        '"JAVA EDITION  /  LOW END v1.1",')

# Keep package identifier and signing key unchanged across releases.
replace("packaging/android/build.gradle", "versionCode 25", "versionCode 26")
replace("packaging/android/build.gradle", "versionName '1.0.0'", "versionName '1.1.0'")

print("Low End v1.1: Android chunk budget 24, Eco 4/4, balanced 7/5, block-style Material buttons, versionCode 26.")
