#!/usr/bin/env python3
"""Replace the native home-page layout, preserving the existing Rust actions.

Unlike the old placeholder overlay this replaces the entire home layout,
so installation progress, labels and action buttons cannot overlap.
"""
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
p = root / "crates/horizon-client/src/android/launcher_pages.rs"
s = p.read_text(encoding="utf-8")
a = s.index("        if page == Page::Play {")
b = s.index("        } else if page.is_catalog() {", a)
new = r'''        if page == Page::Play {
            use horizon_client::official_install::InstallStage;
            let installed = horizon_client::official_install::ready(&self.home);
            let installing = self.worker.is_some();
            let progress = *self.install.lock().unwrap();
            let wide = w >= 700.0;
            let margin = if wide { 24.0 } else { 16.0 };
            let hero_y = 146.0;
            let hero_h = if wide { (h - 390.0).max(220.0) }
                         else { (h - 305.0).max(185.0) };
            let hero_w = w - margin * 2.0;
            let purple = horizon_client::hud::rgba(156, 148, 255, 255);
            let dark = horizon_client::hud::rgba(19, 24, 47, 255);
            let glass = horizon_client::hud::rgba(34, 42, 75, 255);
            let muted = color::MUTED;
            // The home screen has one hero card. Unlike the previous overlay,
            // all copy and progress are placed inside it with fixed spacing.
            ui.rounded(margin, hero_y, hero_w, hero_h, 20.0, dark);
            if wide {
                // GPU-cheap landscape silhouette. A true panorama texture
                // requires a separately implemented textured UI renderer.
                let right_x = w * 0.64;
                let right_w = w - margin - right_x;
                ui.rounded(right_x, hero_y + 1.0, right_w,
                           hero_h - 2.0, 18.0, glass);
                let horizon_y = hero_y + hero_h * 0.72;
                ui.rounded(right_x + 14.0, horizon_y - 26.0,
                           right_w * 0.26, 36.0, 2.0, dark);
                ui.rounded(right_x + right_w * 0.40, horizon_y - 49.0,
                           right_w * 0.19, 59.0, 2.0, dark);
                ui.rounded(right_x + right_w * 0.65, horizon_y - 20.0,
                           right_w * 0.28, 30.0, 2.0, dark);
                ui.rounded(right_x + 10.0, horizon_y + 10.0,
                           right_w - 20.0, 9.0, 3.0, purple);
            }
            let text_x = margin + 24.0;
            let hero_text_width = if wide { w * 0.59 - text_x }
                                  else { hero_w - 48.0 };
            let heading = if installing {
                tr("Getting your game ready")
            } else if installed {
                tr("Ready to play")
            } else {
                tr("Minecraft Java on Android Native")
            };
            let heading = ui.fit_text(Face::Medium, if wide { 29.0 } else { 23.0 },
                                      heading, hero_text_width);
            ui.text(Face::Medium, if wide { 29.0 } else { 23.0 },
                    text_x, hero_y + 27.0, color::TEXT, &heading);
            let profile = format!("Minecraft 26.3  /  Profile {}", self.catalog.config.profile);
            ui.text(Face::Regular, 16.0, text_x, hero_y + 73.0, muted, &profile);
            // Real installation progress, no decorative pseudo-glyph bars.
            let current = InstallStage::ALL.iter()
                .position(|stage| *stage == progress.stage).unwrap_or(0);
            let fraction = if progress.total > 0 {
                (progress.done as f32 / progress.total as f32).clamp(0.0, 1.0)
            } else { 0.0 };
            let overall = ((current as f32 + fraction) / 6.0).clamp(0.0, 1.0);
            let bar_y = hero_y + 102.0;
            let bar_w = hero_text_width.min(470.0).max(50.0);
            ui.rounded(text_x, bar_y, bar_w, 6.0, 3.0, glass);
            if installing && overall > 0.0 {
                ui.rounded(text_x, bar_y, bar_w * overall, 6.0, 3.0, purple);
            } else if installed {
                ui.rounded(text_x, bar_y, bar_w, 6.0, 3.0, purple);
            }
            let lines: [String; 3] = if installing {
                [
                    format!("01  {}", tr("Download resources from Mojang")),
                    format!("02  {}", tr("Install and verify on this phone")),
                    format!("03  {}  {:.0}%", tr("Getting your game ready"), overall * 100.0),
                ]
            } else if installed {
                [
                    format!("01  {}", tr("Open a world or join a Java server")),
                    format!("02  {}", tr("Touch setup: Options > Controls")),
                    format!("03  {}", tr("Find packs and .hmod in the tabs")),
                ]
            } else {
                [
                    format!("01  {}", tr("Download resources from Mojang")),
                    format!("02  {}", tr("Install and verify on this phone")),
                    format!("03  {}", tr("Play offline or sign in for servers")),
                ]
            };
            let line_step = if hero_h >= 290.0 { 38.0 } else { 27.0 };
            for (i, line) in lines.iter().enumerate() {
                let line = ui.fit_text(Face::Regular, 15.0, line, hero_text_width);
                ui.text(Face::Regular, 15.0, text_x,
                        hero_y + 127.0 + i as f32 * line_step, muted, &line);
            }
            // Below-hero action cards use the same existing profile/settings
            // actions as the old UI; they are not decorative.
            let cards_y = hero_y + hero_h + 18.0;
            let card_h = 62.0;
            if wide {
                let gap = 18.0;
                let card_w = (hero_w - gap) * 0.5;
                button(&mut ui, &mut self.targets,
                    [margin, cards_y, card_w, card_h],
                    tr("Choose profile"), Action::Profile, false);
                button(&mut ui, &mut self.targets,
                    [margin + card_w + gap, cards_y, card_w, card_h],
                    tr("Launch settings"), Action::Page(Page::Settings), false);
                // Secondary card subtitles are purely descriptive; the same
                // full-card tap targets remain fully functional.
                ui.text(Face::Regular, 12.0, margin + 16.0,
                    cards_y + 39.0, color::MUTED,
                    &format!("Профиль {}", self.catalog.config.profile));
                ui.text(Face::Regular, 12.0,
                    margin + card_w + gap + 16.0,
                    cards_y + 39.0, color::MUTED,
                    "Настройки лаунчера");
            } else if h > 580.0 {
                button(&mut ui, &mut self.targets,
                    [margin, cards_y, hero_w * 0.48, 45.0],
                    tr("Choose profile"), Action::Profile, false);
                button(&mut ui, &mut self.targets,
                    [margin + hero_w * 0.50, cards_y, hero_w * 0.50, 45.0],
                    tr("Launch settings"), Action::Page(Page::Settings), false);
            }
            // Keep a real installation/play action, never an inert screenshot.
            if installing {
                let status = format!("{}  {:.0}%", tr("Getting your game ready"),
                                     overall * 100.0);
                ui.text(Face::Medium, 17.0, margin + 8.0,
                        h - 73.0, color::TEXT, &status);
            } else {
                button(&mut ui, &mut self.targets,
                    [margin, h - 88.0, if wide { 365.0 } else { hero_w }, 54.0],
                    if installed { tr("Play") }
                    else if self.error.is_some() { tr("Retry installation") }
                    else { tr("Download Minecraft 26.3") },
                    Action::Play, true);
            }
'''
s = s[:a] + new + s[b:]
# Keep existing header, tabs and hit-testing. Replace pill geometry and
# active colors without introducing Android Material You dynamic colors.
old = '''        2.0,
        if accent { color::launcher_accent() } else { color::RAISED },
    );
    let padding ='''
if s.count(old) != 1:
    raise RuntimeError("Button skin anchor changed; stop instead of shipping bad UI")
s = s.replace(old, '''        (h * 0.5).min(25.0),
        if accent { horizon_client::hud::rgba(153, 143, 255, 255) }
        else { horizon_client::hud::rgba(33, 40, 68, 255) },
    );
    let padding =''', 1)
# Give the header the same three-part hierarchy as the supplied reference:
# block icon, large product name, and small Russian subtitle.
header = '''        ui.text(
            Face::Medium,
            if w < 400.0 {'''
if s.count(header) != 1:
    raise RuntimeError("Native header anchor changed")
s = s.replace(header, '''        if w >= 700.0 {
            ui.rounded(32.0, 22.0, 58.0, 58.0, 10.0,
                horizon_client::hud::rgba(108, 82, 54, 255));
            ui.rounded(32.0, 22.0, 58.0, 21.0, 7.0,
                horizon_client::hud::rgba(91, 161, 70, 255));
            ui.rounded(40.0, 25.0, 17.0, 9.0, 2.0,
                horizon_client::hud::rgba(131, 193, 85, 255));
        }
        ui.text(
            Face::Medium,
            if w < 400.0 {''', 1)
old_x = '''            32.0,
            if w < 700.0 { 12.0 } else { 28.0 },
            color::TEXT,
            &format!("Horizon Android {}", crate::backend::VERSION),
        );'''
if s.count(old_x) != 1:
    raise RuntimeError("Native header title anchor changed")
s = s.replace(old_x, '''            if w >= 700.0 { 110.0 } else { 32.0 },
            if w < 700.0 { 12.0 } else { 20.0 },
            color::TEXT,
            &format!("Horizon Android {}", crate::backend::VERSION),
        );
        if w >= 700.0 {
            ui.text(Face::Regular, 14.0, 110.0, 63.0,
                color::MUTED, tr("The best launcher for Minecraft Java"));
        }''', 1)
# Ensure translation is available without loading a new font each frame.
catalog = root / "crates/horizon-client/src/android/catalog.rs"
c = catalog.read_text(encoding="utf-8")
anchor = '        "On" => "Вкл.",'
if c.count(anchor) != 1:
    raise RuntimeError("Translation catalog anchor changed")
c = c.replace(anchor,
    '        "The best launcher for Minecraft Java" => "Лучший лаунчер для Minecraft Java",\n' + anchor, 1)
catalog.write_text(c, encoding="utf-8")
p.write_text(s, encoding="utf-8")
print("Rebuilt functional home layout: no text collisions, actual progress and action cards.")
