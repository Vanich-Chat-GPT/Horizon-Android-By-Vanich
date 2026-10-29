#!/usr/bin/env python3
"""v1.3.3 online catalog usability and zero-copy visible-row rendering.

Use the existing real Horizon mods, native shader and Modrinth shader sources.
No fictitious 'all mods' database or nonfunctional search controls.
"""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
p=root/"crates/horizon-client/src/android/launcher_pages.rs"
s=p.read_text(encoding="utf-8")
def patch(a,b):
 global s
 if s.count(a)!=1: raise RuntimeError(f"catalog patch anchor count={s.count(a)}: {a[:100]}")
 s=s.replace(a,b,1)
# Results are already fetched by the online catalog. Show truthful page size
# and pagination state instead of claiming a full offline index.
patch('''            let hint = ui.fit_text(Face::Regular, 14.0, hint, w - 64.0);
            ui.text(Face::Regular, 14.0, 32.0, 270.0, color::MUTED, &hint);''',
'''            let hint = ui.fit_text(Face::Regular, 14.0, hint, w - 64.0);
            ui.text(Face::Regular, 14.0, 32.0, 270.0, color::MUTED, &hint);
            let page_number = self.catalog.offset / 24 + 1;
            let listing = format!("Online catalog  /  Page {}  /  {} results",
                page_number, self.catalog.results.len());
            let listing = ui.fit_text(Face::Regular, 13.0, &listing, w - 64.0);
            ui.text(Face::Regular, 13.0, 32.0, 286.0, color::MUTED, &listing);''')
# Keep the real installed content, search, and pagination actions. Avoid
# materializing title/summary text for offscreen catalog results.
patch('''                let download = self.catalog.download_label(p);
                if download.is_none() {
                    self.list_targets
                        .push(([w - 150.0, y, 118.0, 70.0], Action::Install(i)));
                }
                if y < top || y + 70.0 > bottom {
                    continue;
                }
                let title =''',
'''                if y < top || y + 70.0 > bottom {
                    continue;
                }
                let download = self.catalog.download_label(p);
                if download.is_none() {
                    self.list_targets
                        .push(([w - 150.0, y, 118.0, 70.0], Action::Install(i)));
                }
                let title =''')
# Request 24 real results from the online provider instead of 12. Keep
# pagination increments in sync so pages never skip or repeat entries.
patch("                self.catalog.offset += 12;",
      "                self.catalog.offset += 24;")
patch("self.catalog.offset = self.catalog.offset.saturating_sub(12);",
      "self.catalog.offset = self.catalog.offset.saturating_sub(24);")
p.write_text(s,encoding="utf-8")
backend=root/"crates/horizon-client/src/android/catalog.rs"
b=backend.read_text(encoding="utf-8")
assert b.count("            query.limit = 12;") == 1
backend.write_text(b.replace("            query.limit = 12;",
                             "            query.limit = 24;", 1), encoding="utf-8")
print("Real online Horizon mods and shader catalogs: page feedback and visible-row-only work.")
