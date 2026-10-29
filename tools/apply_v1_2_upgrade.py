#!/usr/bin/env python3
"""v1.2.0 improvements: preserve visual quality and default game locale to Russian."""
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
def patch(path,old,new):
    file=root/path
    data=file.read_text(encoding="utf-8")
    if data.count(old)!=1: raise RuntimeError(f"{path}: anchor count {data.count(old)} {old[:90]}")
    file.write_text(data.replace(old,new,1),encoding="utf-8")

# Android defaults to Russian in Minecraft itself (not only the native
# launcher). Previously saved options.txt language remains authoritative.
patch("crates/horizon-client/src/settings.rs",
      '            language: "en_us".into(),',
      '''            language: if cfg!(target_os = "android") {
                "ru_ru"
            } else {
                "en_us"
            }.into(),''')

# Show truthful, non-destructive quality controls: all pixels of the selected
# preset are retained; queue pacing only changes when chunk results are handled.
# The quality profile 100% stays available to users.
# Increment APK version with persistent package ID and SAME signing key.
patch("packaging/android/build.gradle","versionCode 27","versionCode 28")
patch("packaging/android/build.gradle","versionName '1.1.1'","versionName '1.2.0'")
patch("crates/horizon-client/src/android/launcher_pages.rs",
      '"JAVA EDITION  /  LOW END v1.1",',
      '"JAVA EDITION  /  v1.2 ANDROID",')
print("v1.2: game locale ru_ru by default, preserve per-user overrides, versionCode 28")
