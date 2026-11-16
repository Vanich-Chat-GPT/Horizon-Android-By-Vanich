# Version metadata validator

The Rust Core parses the Mojang version-specific JSON after a version-index entry has been selected.

Validated fields:
- requested version ID matches metadata ID;
- main class is present;
- optional Java major version is in a supported numeric range;
- asset-index URL is HTTPS on the official metadata host;
- client JAR URL is HTTPS on the official game-data host;
- library artifact and classifier URLs use the allow-listed Maven hosts;
- SHA-1 and optional SHA-256 values have the correct hexadecimal shape;
- artifact sizes are non-zero;
- relative artifact paths cannot escape the target directory.

The parsed rules, native classifier labels and extract metadata are retained but not evaluated yet. This validator intentionally does not produce an Android download plan. In particular, Linux ARM64 desktop native libraries are not Android Bionic libraries and must not be copied into the Android install.

This module validates metadata only. A later installer must independently verify downloaded bytes against their declared hashes before atomically moving files into the installation.
