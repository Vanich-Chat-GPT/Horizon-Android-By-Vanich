# Microsoft account authentication setup

NOVA uses the Microsoft Authentication Library (MSAL) as a public Android client. No client secret is embedded in the APK. The sign-in chain is:

1. Microsoft OAuth with the delegated `XboxLive.signin` and `offline_access` scopes.
2. Xbox Live user authentication.
3. Xbox Secure Token Service (XSTS) authorization.
4. Minecraft Services token exchange.
5. Minecraft Store entitlement check and Java profile lookup.

The Minecraft access token is encrypted with an AES-GCM key held by Android Keystore. Microsoft refresh credentials remain in MSAL's protected token cache. Tokens and authorization headers must never be written to logs, diagnostics exports, ordinary preferences or Git.

## Required app-registration values

The Android package is `dev.nova.horizon`. Register a native/public-client Android application with Microsoft and configure its MSAL redirect URI:

`msauth://dev.nova.horizon/<BASE64_SIGNATURE_HASH>`

The signature hash must match the certificate that signs the APK being installed. Debug and release signing certificates are different, so their redirect registrations/hashes are not interchangeable.

Provide these build properties locally or as GitHub Actions secrets:

- `MICROSOFT_CLIENT_ID`: the public application/client ID from the app registration
- `MICROSOFT_REDIRECT_SIGNATURE_HASH`: the signature hash for the exact signing certificate

The build generates `msal_config.json` at build time. These values are not committed to source control. A build without them remains usable for launcher settings and diagnostics, but Microsoft sign-in is disabled.

The app registration must have the required delegated Xbox Live permission and be configured for personal Microsoft accounts. Microsoft/Minecraft service access may require additional approval. A service-side 403 or an Xbox account restriction is reported as an error; NOVA does not attempt to bypass it.

Family, age, regional, account-security and parental-control restrictions are respected. If Microsoft or Xbox requires account-holder/family approval, complete that through the official account process; the launcher does not circumvent it.

## Validation boundary

A successful OAuth token alone does not grant Minecraft ownership. NOVA only records Java entitlement after Minecraft Services confirms the account's Java product and returns a valid Minecraft profile. The current launcher still lacks the Java SE runtime and the Android LWJGL/graphics/input/audio bridge, so authentication does not mean that game launch is ready.
