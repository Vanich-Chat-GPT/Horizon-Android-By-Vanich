# Security policy

- OAuth tokens and refresh tokens must never be written to logs.
- Account secrets must be protected with Android Keystore-backed encryption.
- Downloads must be verified against trusted official metadata before activation.
- Files are staged to temporary paths and atomically promoted only after verification.
- World saves must never be removed automatically.
- Diagnostic exports must redact tokens, account identifiers and private paths.
- No telemetry is sent without explicit user consent.
- No license checks, account checks or authentication flows are bypassed.
- Report security issues privately to the repository owner; do not publish credentials or exploit details in issues.
