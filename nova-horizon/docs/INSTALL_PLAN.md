# Android ARM64 installation plan

The current installer planner is deliberately conservative.

- It always plans the version-specific client JAR and asset-index JSON after metadata validation.
- It includes a library's ordinary JAR only when the parser can safely resolve the metadata path and its ordered Mojang rules allow the Android ARM64 profile.
- Unknown rule conditions are not treated as an allow decision.
- Desktop native classifiers are recorded as unresolved requirements; Linux, Windows and macOS binaries are never relabelled as Android/Bionic.
- The plan always returns launchReady=false until a compatible Java SE runtime, native-library bridge, renderer and input/audio integration pass end-to-end checks.

The next installer stage is to expand the asset index into deduplicated asset-object requests and create a durable, cancellable batch transfer. Account entitlement verification must gate game-file downloads.
