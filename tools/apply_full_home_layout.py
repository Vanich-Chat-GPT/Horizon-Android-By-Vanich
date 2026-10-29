#!/usr/bin/env python3
"""Replace the old home page layout with a functional, screenshot-proportioned one.

Runs after the previous launcher overlays. This deliberately changes only the
launcher draw code; game rendering and worlds are untouched.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
p = root / "crates/horizon-client/src/android/launcher_pages.rs"
s = p.read_text(encoding="utf-8")
start = s.index("        if page == Page::Play {\n", s.index("pub(super) fn draw_pages"))
end = s.index("        } else if page.is_catalog() {", start)
home = r'''        if page == Page::Play {
            use horizon_client::official_install::InstallStage;
            let installed = horizon_client::official_install::ready(&self.home);
            let installing = self.worker.is_some();
            let progress = *self.install.lock().unwrap();
            let wide = w >= 700.0 && h >= 560.0;
            let left = if wide { 26.0 } else { 18.0 };
            let usable = w - left * 2.0;
            let hero_y = if wide { 148.0 } else { 146.0 };
            let hero_h = if wide { (h - 392.0).max(225.0) } else { (h - 290.0).max(190.0) };
            // Native dark hero with rounded edges. Background picture is a
            // separate renderer-asset task, not faked as a completed panorama.
            ui.rounded(left, hero_y, usable, hero_h, 21.0, color::RAISED);
            if wide {
                // A restrained dusk-toned backdrop; keep every text line
                // legible and avoid expensive per-frame image allocations.
                let right = left + usable * 0.58;
                ui.rounded(right, hero_y + 4.0, usable * 0.40, hero_h - 8.0,
                    16.0, color::HOVER);
                ui.rounded(right + 14.0, hero_y + hero_h * 0.68,
                    usable * 0.31, hero_h * 0.17, 3.0, color::BG);
                ui.rounded(right + 56.0, hero_y + hero_h * 0.49,
                    usable * 0.12, hero_h * 0.21, 3.0, color::RAISED);
            }
            let text_x = left + 22.0;
            let headline = if installing {
                "Подготовка Minecraft Java"
            } else if installed {
                "Minecraft Java на Android — готово"
            } else {
                "Minecraft Java на Android — нативно"
            };
            let headline = ui.fit_text(Face::Medium, if wide { 27.0 } else { 20.0 },
                headline, if wide { usable * 0.57 } else { usable - 40.0 });
            ui.text(Face::Medium, if wide { 27.0 } else { 20.0 },
                text_x, hero_y + 27.0, color::TEXT, &headline);
            ui.text(Face::Regular, 15.0, text_x, hero_y + 77.0,
                color::MUTED,
                &format!("Minecraft 26.3   /   Профиль {}", self.catalog.config.profile));
            let stage = InstallStage::ALL.iter().position(|x| *x == progress.stage).unwrap_or(0);
            let fraction = if progress.total > 0 {
                (progress.done as f32 / progress.total as f32).clamp(0.0, 1.0)
            } else { 0.0 };
            let overall = if installing {
                (stage as f32 + fraction) / InstallStage::ALL.len() as f32
            } else if installed { 1.0 } else { 0.0 };
            let bar_y = hero_y + 113.0;
            let bar_w = if wide { usable * 0.42 } else { usable - 44.0 };
            ui.rounded(text_x, bar_y, bar_w, 7.0, 3.0, color::BG);
            if overall > 0.0 {
                ui.rounded(text_x, bar_y, bar_w * overall, 7.0, 3.0,
                    color::launcher_accent());
            }
            let lines = if installing {
                [
                    "01  Загрузка ресурсов игры",
                    "02  Проверка файлов Minecraft",
                    "03  Подготовка к запуску",
                ]
            } else if installed {
                [
                    "01  Выберите профиль игры",
                    "02  Настройте управление внутри Minecraft",
                    "03  Играйте офлайн или войдите для серверов",
                ]
            } else {
                [
                    "01  Загрузка ресурсов Mojang",
                    "02  Установка и проверка на устройстве",
                    "03  Играйте офлайн или войдите для серверов",
                ]
            };
            for (index, line) in lines.iter().enumerate() {
                let y = hero_y + 132.0 + index as f32 * 31.0;
                if y + 24.0 < hero_y + hero_h {
                    let line = ui.fit_text(Face::Regular, 14.0, line,
                        if wide { usable * 0.52 } else { usable - 42.0 });
                    ui.text(Face::Regular, 14.0, text_x, y, color::MUTED, &line);
                }
            }
            if wide {
                let card_y = hero_y + hero_h + 15.0;
                let card_w = (usable - 16.0) / 2.0;
                ui.rounded(left, card_y, card_w, 69.0, 16.0, color::RAISED);
                ui.rounded(left + card_w + 16.0, card_y, card_w, 69.0,
                    16.0, color::RAISED);
                button(&mut ui, &mut self.targets,
                    [left + 8.0, card_y + 9.0, card_w - 16.0, 51.0],
                    "Выбор профиля", Action::Profile, false);
                button(&mut ui, &mut self.targets,
                    [left + card_w + 24.0, card_y + 9.0, card_w - 16.0, 51.0],
                    "Дополнительные опции", Action::Page(Page::Settings), false);
            }
            if installing {
                let progress_label = if progress.total > 0 {
                    format!("{}: {} / {}",
                        progress.stage.label(), progress.done, progress.total)
                } else { progress.stage.label().to_owned() };
                let progress_label = ui.fit_text(Face::Regular, 14.0,
                    &progress_label, usable - 28.0);
                ui.text(Face::Regular, 14.0, text_x, h - 78.0,
                    color::MUTED, &progress_label);
            } else {
                button(&mut ui, &mut self.targets,
                    [left, h - 98.0, if wide { usable * 0.33 } else { usable }, 58.0],
                    if installed { "Играть" }
                    else if self.error.is_some() { "Повторить установку" }
                    else { "Скачать Minecraft 26.3" },
                    Action::Play, true);
            }
'''
s = s[:start] + home + s[end:]
p.write_text(s, encoding="utf-8")
print("Native launcher home rebuilt with proportional hero, progress, profile/settings and real actions.")
