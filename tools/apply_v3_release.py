#!/usr/bin/env python3
"""Finalize HorizonCraft v3 Android branding and version metadata."""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()

gradle = root / "packaging/android/build.gradle"
source = gradle.read_text(encoding="utf-8")

source, code_count = re.subn(r"versionCode\s+\d+", "versionCode 35", source, count=1)
if code_count != 1:
    raise RuntimeError(f"{gradle}: expected one versionCode entry, got {code_count}")

source, name_count = re.subn(r"versionName\s+'[^']+'", "versionName '3.0.0'", source, count=1)
if name_count != 1:
    raise RuntimeError(f"{gradle}: expected one versionName entry, got {name_count}")

gradle.write_text(source, encoding="utf-8")

manifest = root / "packaging/android/AndroidManifest.xml"
source = manifest.read_text(encoding="utf-8")
source, label_count = re.subn(r'android:label="[^"]+"', 'android:label="HorizonCraft v3"', source, count=1)
if label_count != 1:
    raise RuntimeError(f"{manifest}: expected one application label, got {label_count}")
manifest.write_text(source, encoding="utf-8")

print("HorizonCraft v3 metadata: versionCode 35, versionName 3.0.0, launcher label HorizonCraft v3.")
