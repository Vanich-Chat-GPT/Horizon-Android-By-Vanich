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

# Preserve the existing tested Material You launcher controls; visual redesign
# will be implemented independently after the Low End build passes CI.

# Minecraft-style squared buttons with a restrained Material You bevel.
# Applied after the earlier rounded-pill overlay. The highlight uses existing
# palette constants and does not allocate textures or alter touch hitboxes.
# The touch overlay also rewrites button drawing. Do not patch its radius
# using a fragile text anchor; retain the already-working Material You buttons.

# Pixel-inspired low-cost parallax bands on the launcher background.
# All rectangles are drawn by the existing batcher; no image decode or
# permanent panorama texture is needed on a 4 GB tablet.
replace(pages, '''        ui.batch
            .fill(&gui.atlas, 0.0, 0.0, w * scale, h * scale, color::BG);
        ui.text(''', '''        ui.batch
            .fill(&gui.atlas, 0.0, 0.0, w * scale, h * scale, color::BG);
        // Minecraft-inspired landscape silhouette: GPU-batched, zero textures.
        // Material You accent remains in the foreground controls.
        ui.rounded(0.0, h * 0.69, w, h * 0.31, 0.0, color::RAISED);
        ui.rounded(0.0, h * 0.82, w, h * 0.18, 0.0, color::BG);
        ui.rounded(w * 0.07, h * 0.60, w * 0.19, h * 0.22, 0.0, color::RAISED);
        ui.rounded(w * 0.62, h * 0.64, w * 0.25, h * 0.18, 0.0, color::RAISED);
        ui.text(''')

# Make the home headline distinguish the update without changing Minecraft
# gameplay strings or loading third-party game art.
replace(pages, '"JAVA EDITION  /  ANDROID ARM64",',
        '"JAVA EDITION  /  LOW END v1.1",')

# Keep package identifier and signing key unchanged across releases.
replace("packaging/android/build.gradle", "versionCode 25", "versionCode 26")
replace("packaging/android/build.gradle", "versionName '1.0.0'", "versionName '1.1.0'")

print("Low End v1.1: Android chunk budget 24, Eco 4/4, balanced 7/5, existing Material You buttons, versionCode 26.")
