#!/usr/bin/env python3
"""HorizonCraft: responsive screenshot-inspired home screen, real actions only.

Keeps native buttons, page navigation, profile, sign-in and installer logic.
No expensive per-frame image decoding, external assets or simulated buttons.
"""
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
p = root / "crates/horizon-client/src/android/launcher_pages.rs"
s = p.read_text(encoding="utf-8")
def replace(old,new):
    global s
    n=s.count(old)
    if n != 1:
        raise RuntimeError(f"launcher UI anchor count {n}: {old[:85]!r}")
    s=s.replace(old,new,1)

# Screenshot-like pill navigation; native targets remain unchanged.
replace('''        2.0,
        if accent { color::launcher_accent() } else { color::RAISED },
    );
    let padding =''',
'''        (h * 0.5).min(24.0),
        if accent { color::launcher_accent() } else { color::RAISED },
    );
    let padding =''')
# Subheading is localized and does not displace the login or tabs.
replace('''            &format!("Horizon Android {}", crate::backend::VERSION),
        );
        button(''',
'''            &format!("Horizon Android {}", crate::backend::VERSION),
        );
        if w >= 700.0 {
            ui.text(Face::Regular, 14.0, 32.0, 68.0, color::MUTED,
                tr("The best launcher for Minecraft Java"));
        }
        button(''')
# Rounded hero surface and a GPU-cheap decorative right-side landscape.
# On small displays preserve full-width text and original touch targets.
replace('''        if page == Page::Play {
            use horizon_client::official_install::InstallStage;''',
'''        if page == Page::Play {
            // Decorative layers render behind the existing functional home
            // controls; no extra tap targets or allocations.
            if w >= 700.0 && h >= 500.0 {
                let hero_h = (h - 290.0).max(215.0);
                ui.rounded(24.0, 148.0, w - 48.0, hero_h, 22.0, color::RAISED);
                ui.rounded(w * 0.62, 148.0, w * 0.38 - 24.0, hero_h,
                    22.0, color::HOVER);
                // Block-shaped skyline; clipped to the hero visually by
                // staying within its lower-right region.
                ui.rounded(w * 0.72, 148.0 + hero_h * 0.55,
                    w * 0.11, hero_h * 0.20, 0.0, color::RAISED);
                ui.rounded(w * 0.81, 148.0 + hero_h * 0.43,
                    w * 0.12, hero_h * 0.32, 0.0, color::RAISED);
                ui.rounded(w * 0.67, 148.0 + hero_h * 0.74,
                    w * 0.27, hero_h * 0.18, 0.0, color::BG);
            }
            use horizon_client::official_install::InstallStage;''')
# Keep text above decoration and allow narrow screens to remain functional.
replace('''            let top = 160.0;
            ui.text(''',
'''            let top = if w >= 700.0 { 174.0 } else { 160.0 };
            ui.text(''')
p.write_text(s,encoding="utf-8")
catalog = root / "crates/horizon-client/src/android/catalog.rs"
c=catalog.read_text(encoding="utf-8")
anchor='        "On" => "Вкл.",'
if c.count(anchor)!=1: raise RuntimeError("Russian catalog anchor changed")
c=c.replace(anchor,'        "The best launcher for Minecraft Java" => "Лучший лаунчер для Minecraft Java",\n'+anchor,1)
catalog.write_text(c,encoding="utf-8")
print("Responsive native home: functional pill tabs, real login/profile/installer and low-overhead hero.")
