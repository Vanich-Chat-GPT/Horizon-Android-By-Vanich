#!/usr/bin/env python3
"""Rebuild the launcher chrome to the user's 1536x915 reference layout.

Apply AFTER legacy overlays and screenshot_home, BEFORE compilation. The game
engine and game touch controls are not modified by this file. This is a native
Rust HUD implementation, not a web mock-up. Panorama art is a separate pending
asset and must not be replaced by a fake gradient claiming pixel parity.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
p=root/"crates/horizon-client/src/android/launcher_pages.rs"
s=p.read_text(encoding="utf-8")
def section(a,b,new):
 global s
 i=s.find(a)
 j=s.find(b,i+len(a))
 if i<0 or j<0 or s.find(a,i+1)>=0:
  raise RuntimeError(f"reference UI anchor missing/ambiguous: {a[:60]}")
 s=s[:i]+new+s[j:]
# Rebuild all chrome: header, auth, six functional navigation tabs.
# The reference uses x/1536 and y/915. Clamp touch targets for density.
section('''        ui.text(
            Face::Medium,
            if w < 400.0 {''',
'''        let compact = w < 700.0;''',
'''        // Reference artwork coordinate system: 1536 x 915.
        // All tap targets are recorded by the native button() helper.
        let sx = (w / 1536.0).max(0.35);
        let sy = (h / 915.0).max(0.35);
        let large = w >= 700.0 && h >= 500.0;
        let ink = color::hex(0xf2f0ff, 255);
        let subtle = color::hex(0xa6acd0, 255);
        let plate = color::hex(0x222b4d, 255);
        let lavender = color::hex(0xa49bff, 255);
        if large {
            // Header: square grass-block badge, title, caption, account.
            ui.rounded(40.0*sx, 62.0*sy, 72.0*sx, 76.0*sy,
                14.0*sx, color::hex(0x426d36,255));
            ui.rounded(40.0*sx, 110.0*sy, 72.0*sx, 28.0*sy,
                7.0*sx, color::hex(0x74533a,255));
            ui.text(Face::Medium, 33.0*sx, 137.0*sx, 66.0*sy,
                ink, "HorizonCraft");
            ui.text(Face::Regular, 19.0*sx, 137.0*sx, 111.0*sy,
                subtle, tr("The best launcher for Minecraft Java"));
            button(&mut ui, &mut self.targets,
                [1153.0*sx,71.0*sy,290.0*sx,60.0*sy],
                &self.login.status(&self.catalog.config.name),
                Action::Account, self.login.signed_in);
            let nav_labels = ["Играть","Моды","Ресурсы",
                              "Шейдеры","Установлено","Настройки"];
            for (i, page) in Page::ALL.iter().enumerate() {
                let x = 40.0*sx + i as f32* (1458.0*sx / 6.0);
                let rect = [x,166.0*sy, 228.0*sx, 65.0*sy];
                // Native page actions, never decorative labels.
                button(&mut ui, &mut self.targets, rect, nav_labels[i],
                    Action::Page(*page), *page == self.catalog.page);
            }
        } else {
            ui.text(Face::Medium,24.0,20.0,12.0,ink,"HorizonCraft");
            button(&mut ui,&mut self.targets,
                [20.0,48.0,w-40.0,38.0],
                &self.login.status(&self.catalog.config.name),
                Action::Account,self.login.signed_in);
            let tabs = Page::ALL.len() as f32;
            let width = (w-16.0)/tabs;
            for (i,page) in Page::ALL.iter().enumerate() {
                button(&mut ui,&mut self.targets,
                    [8.0+i as f32*width,94.0,width-3.0,44.0],
                    page.name(),Action::Page(*page),
                    *page==self.catalog.page);
            }
        }
''')
# Remove the old block skyline: it does not resemble the reference photograph.
section('''        if page == Page::Play {
            // Decorative layers render behind the existing functional home''',
'''            use horizon_client::official_install::InstallStage;''',
'''        if page == Page::Play {
            if large {
                // Image-backed panorama is pending. Use a restrained dark
                // card until a licensed, optimized texture is bundled.
                ui.rounded(40.0*sx,251.0*sy,1458.0*sx,389.0*sy,
                    26.0*sx,plate);
                ui.rounded(42.0*sx,253.0*sy,1454.0*sx,385.0*sy,
                    24.0*sx,color::hex(0x121b38,255));
                ui.text(Face::Medium,33.0*sx,230.0*sx,288.0*sy,
                    ink,"Minecraft Java на Android —");
                ui.text(Face::Medium,33.0*sx,230.0*sx,329.0*sy,
                    ink,"нативно");
                // Real profile, actual installer and action button below
                // continue to be drawn by the existing launcher code.
            }
''')
p.write_text(s,encoding="utf-8")
print("Native reference chrome applied. Panorama texture and device QA pending.")
