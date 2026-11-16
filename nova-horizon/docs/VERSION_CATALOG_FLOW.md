# Version catalog and descriptor flow

1. The Android application retrieves Mojang's public version manifest over HTTPS from piston-meta.mojang.com.
2. Redirects remain restricted to that same HTTPS host; response bytes have a fixed maximum size.
3. Rust Core parses the manifest, validates version identifiers, duplicate entries, SHA-1 syntax, official descriptor origin and the latest release/snapshot references.
4. Rust serializes the validated descriptor catalogue back to the Android app. The UI can search and select entries without treating an entry as an installed game.
5. When a user requests inspection of one version, Android fetches its JSON descriptor from the exact official metadata host.
6. Android compares the descriptor bytes against the SHA-1 published in the already validated version index.
7. Rust validates the descriptor schema and artifact metadata, including client JAR, asset-index and library origins, hash shapes, byte sizes and safe relative paths.
8. Only a small summary returns to the UI. No game archive is downloaded in this step.

This does not resolve Mojang OS rules or choose Android native libraries. In particular, desktop Linux natives are not Android/Bionic artifacts. No launch readiness, entitlement, installation, or game compatibility is inferred from a descriptor that passed validation.
