#!/usr/bin/env python3
"""Custom touch editor and conservative chunk-stutter performance tuning.

Run AFTER apply_vanich_overlay.py. Upstream controls are already real; this
extends the native editor and graphics profiles without emulating input.
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()

def replace(path: str, before: str, after: str, expected: int = 1) -> None:
    file = ROOT / path
    data = file.read_text(encoding="utf-8")
    count = data.count(before)
    if count != expected:
        raise RuntimeError(f"{path}: expected {expected} match(es), got {count}: {before[:95]!r}")
    file.write_text(data.replace(before, after), encoding="utf-8")

layout = "crates/horizon-client/src/touch/layout.rs"
editor = "crates/horizon-client/src/touch/editor.rs"
pages = "crates/horizon-client/src/android/launcher_pages.rs"
catalog = "crates/horizon-client/src/android/catalog.rs"

# Persist snap-to-grid in horizon-touch.json; existing layouts deserialize via
# #[serde(default)] so old players don't lose their button placements.
replace(layout, "    pub button_scale: f32,\n", "    pub button_scale: f32,\n    pub snap_to_grid: bool,\n")
replace(layout, "            button_scale: 1.0,\n", "            button_scale: 1.0,\n            snap_to_grid: false,\n")
# Allow larger controls on high-density phones, but retain normalized layout
# bounds so editing cannot strand buttons outside the screen.
replace(layout, "self.size = self.size.clamp(0.045, 0.45);",
        "self.size = self.size.clamp(0.045, 0.55);")
replace(layout, "self.button_scale.clamp(0.5, 2.0)",
        "self.button_scale.clamp(0.5, 3.0)")
# Actual in-game touch editor. Existing features: dragging, 0..100% alpha,
# save/cancel/reset, 32 custom buttons. Add precise movement snapping.
replace(editor,
        '''            } else if layout::contains([0.02, 0.13, 0.335, 0.075], p) {
                e.palette = !e.palette;''',
        '''            } else if layout::contains([0.70, 0.04, 0.28, 0.075], p) {
                self.settings.snap_to_grid = !self.settings.snap_to_grid;
                e.drag = None;
            } else if layout::contains([0.02, 0.13, 0.335, 0.075], p) {
                e.palette = !e.palette;''')
replace(editor,
        '''                    if self.settings.left_handed {
                        center[0] = 1.0 - center[0];
                    }
                    // Match the displayed size''',
        '''                    if self.settings.left_handed {
                        center[0] = 1.0 - center[0];
                    }
                    if self.settings.snap_to_grid {
                        const STEP: f32 = 0.025;
                        center = [
                            (center[0] / STEP).round() * STEP,
                            (center[1] / STEP).round() * STEP,
                        ];
                    }
                    // Match the displayed size''')
replace(editor, "place.size = 0.045 + value * 0.405;",
        "place.size = 0.045 + value * 0.505;", expected=2)
replace(editor, "(p.size - 0.045) / 0.405",
        "(p.size - 0.045) / 0.505", expected=2)
replace(editor,
        '''        for (rect, label) in [
            ([0.02, 0.04, 0.105, 0.075], "Done"),''',
        '''        for (rect, label) in [
            ([0.70, 0.04, 0.28, 0.075], if self.settings.snap_to_grid {
                "Grid 2.5%: ON"
            } else {
                "Grid 2.5%: OFF"
            }),
            ([0.02, 0.04, 0.105, 0.075], "Done"),''')
# Since slider percentages are normalized and the touch overlay can be very
# small, show where to drag. Keep transparent buttons editable via editor.
replace(editor,
        '''        if let Some(selected) = e.selected {
            plate(b, a, [0.32, 0.88, 0.36, 0.07], "Remove button", false);''',
        '''        if let Some(selected) = e.selected {
            b.text(
                a,
                "Drag button to move. Size / Opacity below.",
                w * 0.33,
                h * 0.54,
                text,
                true,
            );
            plate(b, a, [0.32, 0.88, 0.36, 0.07], "Remove button", false);''')

# Chunk spikes are more often limited by CPU/memory than fragment shader FPS.
# Performance profiles should also control CPU-heavy options. Avoid spawning
# extra threads or raising unbounded task queues on 4 GB devices.
replace(pages,
        '''                let (scale, chunks, simulation, max_fps, fancy) = match next {
                    QualityPreset::Eco => (50, 6, 5, 60, false),
                    QualityPreset::Balanced => (75, 9, 7, 60, false),
                    QualityPreset::Quality => (100, 14, 10, 90, true),
                };''',
        '''                let (scale, chunks, simulation, max_fps, fancy) = match next {
                    QualityPreset::Eco => (50, 5, 5, 60, false),
                    QualityPreset::Balanced => (67, 8, 6, 90, false),
                    QualityPreset::Quality => (90, 12, 8, 120, true),
                };''')
replace(pages,
        '''                settings.biome_blend = if fancy { 2 } else { 0 };
                settings.save(&path);''',
        '''                settings.biome_blend = if fancy { 2 } else { 0 };
                // Reduces CPU work and chunk fade allocations during traversal.
                settings.entity_distance = if fancy { 1.0 } else { 0.65 };
                settings.chunk_fade = if fancy { 0.35 } else { 0.0 };
                settings.weather_radius = if fancy { 8 } else { 4 };
                settings.menu_blur = if fancy { 3 } else { 0 };
                settings.vignette = fancy;
                settings.prioritize_chunk_updates = 1;
                settings.save(&path);''')
# Expose existing game's control editor in launch Settings for discoverability
# without fabricating any input path: this label directs user to actual in-game UI.
replace(catalog,
        '''        "Graphics preset" => "Профиль графики",''',
        '''        "Touch customization" => "Настройка кнопок",
        "Edit in game: Options > Controls > Customize Touch" =>
            "В игре: Настройки > Управление > Настроить кнопки",
        "Graphics preset" => "Профиль графики",''')
# The Settings page has a static 10-row viewport following previous overlay.
replace(pages,
        '''                (tr("Graphics preset"), tr(c.quality_preset.label()).into(), Action::GraphicsPreset),''',
        '''                (
                    tr("Touch customization"),
                    tr("Edit in game: Options > Controls > Customize Touch").into(),
                    Action::ShowTouchHelp,
                ),
                (tr("Graphics preset"), tr(c.quality_preset.label()).into(), Action::GraphicsPreset),''')
replace(pages, "    GraphicsPreset,\n", "    GraphicsPreset,\n    ShowTouchHelp,\n")
replace(pages, "10.0 * row_height", "11.0 * row_height", expected=2)
replace(pages,
        '''            Some(Action::GraphicsPreset) => {''',
        '''            Some(Action::ShowTouchHelp) => {
                self.catalog.status =
                    tr("Edit in game: Options > Controls > Customize Touch").into();
            }
            Some(Action::GraphicsPreset) => {''')

# The upstream game thread currently drains and allocates *all* completed
# streaming jobs every update, then performs each lighting/mesh/world mutation
# in the same frame. Limit Android intake to bound per-frame work.
# Queue ownership stays with mpsc, so unprocessed results persist safely until
# the next update. Desktop is unaffected.
replace("crates/horizon-client/src/streaming.rs",
        '''        let received = std::iter::from_fn(|| self.results.try_recv().ok());
        for done in deferred.into_iter().chain(received.collect::<Vec<_>>()) {''',
        '''        let received = std::iter::from_fn(|| self.results.try_recv().ok());
        // Avoid a frame-time spike when many completed chunk meshes, lighting
        // jobs and generated columns arrive at once on mobile CPUs.
        #[cfg(target_os = "android")]
        let received = received.take(48).collect::<Vec<_>>();
        #[cfg(not(target_os = "android"))]
        let received = received.collect::<Vec<_>>();
        for done in deferred.into_iter().chain(received) {''')

print("Native touch editor and graphics/streaming controls patched.")
