#!/usr/bin/env python3
"""Brand the pinned Horizon Android port for NOVA HORIZON without changing game code."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: prepare_horizon_android.py <upstream checkout>")

root = Path(sys.argv[1]).resolve()

def replace_once(relative: str, old: str, new: str) -> None:
    path = root / relative
    if not path.is_file():
        raise SystemExit(f"Missing upstream file: {relative}")
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{relative}: expected exactly one {old!r}, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

replace_once(
    "android/app/build.gradle",
    "applicationId 'com.lukagejak.horizon'",
    "applicationId 'dev.nova.horizon'",
)
replace_once(
    "android/app/src/main/AndroidManifest.xml",
    'android:authorities="com.lukagejak.horizon.update"',
    'android:authorities="dev.nova.horizon.update"',
)
replace_once(
    "android/app/src/main/java/com/lukagejak/horizon/ApkProvider.java",
    'static final String AUTHORITY = "com.lukagejak.horizon.update";',
    'static final String AUTHORITY = "dev.nova.horizon.update";',
)
replace_once(
    "android/app/src/main/res/values/strings.xml",
    "<string name=\"app_name\">Horizon</string>",
    "<string name=\"app_name\">NOVA HORIZON</string>",
)
replace_once(
    "crates/horizon-client/src/android/update.rs",
    'const LATEST: &str = "https://api.github.com/repos/MocLG/horizon-android/releases/latest";',
    'const LATEST: &str = "https://api.github.com/repos/Vanich-Chat-GPT/Horizon-Android-By-Vanich/releases/latest";',
)
replace_once(
    "README.md",
    "Android/data/com.lukagejak.horizon/files/minecraft",
    "Android/data/dev.nova.horizon/files/minecraft",
)
replace_once(
    "docs/android.md",
    "Android/data/com.lukagejak.horizon/files/minecraft",
    "Android/data/dev.nova.horizon/files/minecraft",
)

print("Patched pinned Horizon Android port: NOVA HORIZON / dev.nova.horizon")
