#!/usr/bin/env python3
"""Expose existing real invite-code multiplayer in Russian (no fake relay)."""
from pathlib import Path
import sys
root=Path(sys.argv[1]).resolve()
def replace(path,old,new):
 p=root/path;s=p.read_text(encoding="utf-8");n=s.count(old)
 if n!=1: raise RuntimeError(f"{path}: {n} anchors for {old[:70]}")
 p.write_text(s.replace(old,new,1),encoding="utf-8")
friend="crates/horizon-client/src/friends_screen.rs"
replace(friend,'pub const TITLE: &str = "Play with Friends";','pub const TITLE: &str = "Код для сети";')
replace(friend,'("Invite Code".to_owned(), grey(), y)','("Код для сети".to_owned(), grey(), y)')
replace(friend,'label: "Start Sharing",','label: "Создать код",')
replace(friend,'label: if view.copied { "Copied" } else { "Copy Code" },','label: if view.copied { "Скопировано" } else { "Копировать код" },')
multi="crates/horizon-client/src/multiplayer.rs"
replace(multi,'centered(batch, "Join a Friend", 20.0, u32::MAX);','centered(batch, "Ввести код", 20.0, u32::MAX);')
replace(multi,'                    "Invite Code",\n                    code,','                    "Код друга",\n                    code,')
# Underlying code is validated by horizon_friends::invite::parse and the
# existing real network connector; the short code requires a configured relay.
print("Russian network code screens use existing working invite validation and transport.")
