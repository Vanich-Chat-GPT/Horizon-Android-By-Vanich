#!/usr/bin/env python3
"""Embed the user-supplied scenic reference as a tiny launcher-only atlas sprite.
The image is decoded once, NOT allocated or rendered as a new texture each frame.
"""
from pathlib import Path
import base64,sys
root=Path(sys.argv[1]).resolve()
content=base64.b64decode("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")
assert content.startswith(b"\x89PNG\r\n\x1a\n")
asset=root/"crates/horizon-client/assets/horizoncraft_launcher_banner.png"
asset.parent.mkdir(parents=True,exist_ok=True)
asset.write_bytes(content)
launcher=root/"crates/horizon-client/src/android/launcher.rs"
s=launcher.read_text(encoding="utf-8")
old='''        let gui = game::UiResources {
            atlas: HudAtlas::build(&self.home.join("installer"))?,'''
new='''        // Bundled visual from the user's supplied reference; a tiny static PNG
        // stitched into the existing HUD atlas once during launcher startup.
        let backdrop = self.home.join(
            "installer/assets/minecraft/textures/gui/sprites/horizoncraft/banner.png"
        );
        std::fs::create_dir_all(backdrop.parent().unwrap())?;
        std::fs::write(
            &backdrop,
            include_bytes!("../../assets/horizoncraft_launcher_banner.png"),
        )?;
        let gui = game::UiResources {
            atlas: HudAtlas::build(&self.home.join("installer"))?,'''
if s.count(old)!=1: raise RuntimeError(f"launcher image load anchor mismatch: {s.count(old)}")
launcher.write_text(s.replace(old,new,1),encoding="utf-8")
# Draw the actual panorama portion of the supplied screenshot instead of
# the earlier placeholder rectangular skyline, using the SAME batched renderer.
pages=root/"crates/horizon-client/src/android/launcher_pages.rs"
source=pages.read_text(encoding="utf-8")
start='''            if wide {
                // GPU-cheap landscape silhouette. A true panorama texture'''
end='''            let text_x = margin + 24.0;'''
if source.count(start)!=1 or source.count(end)!=1:
    raise RuntimeError("Cannot locate native screenshot hero for texture replacement")
a=source.index(start)
b=source.index(end,a)
replacement='''            if wide {
                // The scenic banner is stitched into the existing atlas once.
                // Draw it with one sprite quad; no per-frame image decoding.
                let right_x = w * 0.59;
                let right_w = w - margin - right_x;
                ui.batch.sprite_scaled(
                    &gui.atlas, "gui/sprites/horizoncraft/banner",
                    right_x * scale, (hero_y + 1.0) * scale,
                    right_w * scale, (hero_h - 2.0) * scale,
                    u32::MAX,
                );
            }
'''
pages.write_text(source[:a]+replacement+source[b:],encoding="utf-8")
print("Bundled user reference image and native one-quad launcher backdrop.")

