#!/usr/bin/env python3
"""Prepare the pinned Starling/Horizon Android source as NOVA HORIZON."""
from pathlib import Path
import sys

PINNED = "50e0ef409738310524e18f77aa8ee6c4378987ed"
TEXT_SUFFIXES = {".rs", ".java", ".xml", ".py", ".json", ".toml", ".md", ".txt"}

def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one {old!r}, found {count}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare_starling.py <upstream checkout>")
    root = Path(sys.argv[1]).resolve()
    import subprocess
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    if commit != PINNED:
        raise SystemExit(f"unexpected upstream commit: {commit}")

    build = root / "packaging/android/build_apk.py"
    replace_once(build, 'APPLICATION_ID = "io.github.juanluci.starling"', 'APPLICATION_ID = "dev.nova.horizon"')
    replace_once(build, 'LABEL = "Starling"', 'LABEL = "NOVA HORIZON"')
    replace_once(build, 'VERSION_NAME = "0.8.0"', 'VERSION_NAME = "3.0.0"')
    replace_once(build, 'VERSION_CODE = 13', 'VERSION_CODE = 30000')
    replace_once(
        build,
        'apk = out / f"starling{\'-\' + variant if variant else \'\'}-{VERSION_NAME}-{args.abi}.apk"',
        'apk = out / f"NOVA-HORIZON{\'-\' + variant if variant else \'\'}-{VERSION_NAME}-{args.abi}.apk"',
    )

    # Java package declarations, Android manifest component names, R.java generation,
    # and JNI symbol names must all agree.
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            try:
                source = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            updated = source.replace("io.github.juanluci.starling", "dev.nova.horizon")
            updated = updated.replace("io/github/juanluci/starling", "dev/nova/horizon")
            if updated != source:
                path.write_text(updated, encoding="utf-8")

    # Brand the Android-facing strings without renaming Java/Rust symbols.
    replacements = {
        "packaging/android/res/values/strings_ui.xml": [
            ("Starling at work", "NOVA HORIZON is working"),
            ("Starling is working", "NOVA HORIZON is working"),
            (">Starling<", ">NOVA HORIZON<"),
        ],
        "packaging/android/res/values/folders.xml": [
            ("choose Starling in its menu", "choose NOVA HORIZON in its menu"),
        ],
        "packaging/android/res/values/diagnostics.xml": [
            ("Starling did not finish starting last time", "NOVA HORIZON did not finish starting last time"),
        ],
        "packaging/android/java/io/github/juanluci/starling/LauncherActivity.java": [
            ("Handing the file to Starling...", "Handing the file to NOVA HORIZON..."),
        ],
        "packaging/android/java/io/github/juanluci/starling/StarlingActivity.java": [
            ('? "StarlingDev"', '? "NOVA HORIZON Dev"'),
            (': id.endsWith(".preview") ? "StarlingPreview" : "Starling";',
             ': id.endsWith(".preview") ? "NOVA HORIZON Preview" : "NOVA HORIZON";'),
        ],
    }
    for relative, pairs in replacements.items():
        path = root / relative
        for old, new in pairs:
            source = path.read_text(encoding="utf-8")
            if old not in source:
                raise SystemExit(f"{relative}: branding anchor not found: {old!r}")
            path.write_text(source.replace(old, new), encoding="utf-8")

    ui_script = Path(__file__).resolve().parents[1] / "ui" / "integrate_launcher.py"
    subprocess.run([sys.executable, str(ui_script), str(root)], check=True)

    # The pinned Android document provider references a nonexistent GameFolder.context field.
    # DocumentsProvider.getContext() is already the supported source of this context.
    provider = root / "packaging/android/java/dev/nova/horizon/GameFolderProvider.java"
    if not provider.exists():
        provider = root / "packaging/android/java/io/github/juanluci/starling/GameFolderProvider.java"
    replace_once(
        provider,
        "        GameFolder.context = context;\\n",
        "",
    )
    print("Prepared NOVA HORIZON 3.0.0: Rust 26.3, custom launcher, Russian defaults and Android UI.")

if __name__ == "__main__":
    main()
