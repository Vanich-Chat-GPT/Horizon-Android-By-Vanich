#!/usr/bin/env python3
"""v1.1.1 Low End: conservative Android-only frame budget and Minecraft-style launcher.
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
        "let received = received.take(if self.loading { 32 } else { 16 }).collect::<Vec<_>>();")

# Preserve the existing tested Material You launcher controls; visual redesign
# will be implemented independently after the Low End build passes CI.

# Visible stage/byte progress in the native installer. A notification after
# process termination needs an Android foreground service (not yet present).
replace(pages, '''                let bar_y = h - 152.0;
                ui.rounded(32.0, bar_y, w - 64.0, 4.0, 2.0, color::RAISED);''', '''                let bar_y = h - 152.0;
                ui.text(Face::Medium, 15.0, 32.0, bar_y - 25.0,
                    color::TEXT, &format!("Installing: {:.0}%", overall * 100.0));
                ui.rounded(32.0, bar_y, w - 64.0, 4.0, 2.0, color::RAISED);''')

# Keep package identifier and signing key unchanged across releases.
replace("packaging/android/build.gradle", "versionCode 25", "versionCode 27")
replace("packaging/android/build.gradle", "versionName '1.0.0'", "versionName '1.1.1'")

print("Low End v1.1: Android chunk budget 16 normal / 32 initial load, Eco 4/4, balanced 7/5, existing Material You buttons, versionCode 27.")
