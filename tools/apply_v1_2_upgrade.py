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

# Limit simultaneous expensive Android generation jobs, not render distance.
# This backpressure applies at scheduling, before the workers allocate world
# generation scratch buffers. Completed chunks are NOT dropped.
patch("crates/horizon-client/src/streaming.rs",
      "        if let Some(wanted) = self.generation_scan.candidates(input, workers * 3) {",
      """        // On memory-constrained Android, do not queue an ever-growing batch
        // of generator work while the renderer processes previous results.
        // This preserves visible chunk detail and only adjusts pacing.
        let budget = if cfg!(target_os = "android") {
            workers.saturating_mul(4).saturating_sub(self.generating.len())
                .min(workers.saturating_mul(2))
        } else {
            workers * 3
        };
        if budget == 0 { return; }
        if let Some(wanted) = self.generation_scan.candidates(input, budget) {""")

# Show truthful, non-destructive quality controls: all pixels of the selected
# preset are retained; queue pacing only changes when chunk results are handled.
# The quality profile 100% stays available to users.
# Display name can change without changing Android applicationId or signing identity.
patch("packaging/android/AndroidManifest.xml",
      'android:label="Horizon Android"',
      'android:label="HorizonCraft"')
# Increment APK version with persistent package ID and SAME signing key.
patch("packaging/android/build.gradle","versionCode 27","versionCode 33")
patch("packaging/android/build.gradle","versionName '1.1.1'","versionName '1.3.3'")
print("v1.3.3: Russian game, bounded chunk work, versionCode 33")
