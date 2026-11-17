#!/usr/bin/env python3
"""Apply the small, auditable NOVA HORIZON identity patch to pinned Amethyst source."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: prepare_amethyst.py <Amethyst checkout>")

root = Path(sys.argv[1]).resolve()
gradle_file = root / "app_pojavlauncher" / "build.gradle"
if not gradle_file.is_file():
    raise SystemExit(f"Amethyst Gradle file not found: {gradle_file}")

text = gradle_file.read_text(encoding="utf-8")

replacements = [
    ('String semVer = "1.1.7"', 'String semVer = "3.0.0"'),
    ('applicationId "org.angelauramc.amethyst"', 'applicationId "dev.nova.horizon"'),
    ("            applicationIdSuffix '.debug'\n", ""),
    ('resValue "string", "app_name", "Amethyst (Debug)"', 'resValue "string", "app_name", "NOVA HORIZON"'),
    ('resValue "string", "app_short_name", "Amethyst (Debug)"', 'resValue "string", "app_short_name", "NOVA HORIZON"'),
    ('resValue "string", "app_name", "Amethyst"', 'resValue "string", "app_name", "NOVA HORIZON"'),
    ('resValue "string", "app_short_name", "Amethyst"', 'resValue "string", "app_short_name", "NOVA HORIZON"'),
    ("'org.angelauramc.amethyst.debug'", "'dev.nova.horizon'"),
    ("'org.angelauramc.amethyst'", "'dev.nova.horizon'"),
    ("'org.angelauramc.amethyst.scoped.gamefolder.debug'", "'dev.nova.horizon.scoped.gamefolder'"),
    ("'org.angelauramc.amethyst.scoped.controlfolder.debug'", "'dev.nova.horizon.scoped.controlfolder'"),
    ("'org.angelauramc.amethyst.scoped.gamefolder'", "'dev.nova.horizon.scoped.gamefolder'"),
]

for old, new in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one occurrence of {old!r}, found {count}")
    text = text.replace(old, new, 1)

gradle_file.write_text(text, encoding="utf-8")

for forbidden in (
    'applicationId "org.angelauramc.amethyst"',
    "applicationIdSuffix '.debug'",
    "'org.angelauramc.amethyst.debug'",
    "'org.angelauramc.amethyst.scoped.gamefolder.debug'",
):
    if forbidden in text:
        raise SystemExit(f"Unpatched upstream application identity remains: {forbidden}")

if 'applicationId "dev.nova.horizon"' not in text:
    raise SystemExit("NOVA HORIZON application ID was not applied")

print("Patched pinned Amethyst source as dev.nova.horizon / NOVA HORIZON")
