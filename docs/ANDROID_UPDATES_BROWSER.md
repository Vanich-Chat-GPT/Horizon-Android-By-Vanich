# Browser-only Android signing setup (GitHub Codespaces)

Use this guide from Chrome on Android; no Termux or PC required.

## 1. Start a private Codespace

Open the repository **Code** → **Codespaces** → **Create codespace on main**. Codespaces availability and quota depend on your GitHub account.

## 2. Run one command in the Codespace terminal

Paste this **one line** (it installs Java if missing, creates the persistent keystore, stores a local Base64 copy, and prints only a success message; it does NOT print secrets to the terminal):

```bash
set -e; if ! command -v keytool >/dev/null 2>&1; then sudo apt-get update -qq && sudo apt-get install -y openjdk-17-jdk-headless; fi; mkdir -p "$HOME/horizon-signing"; chmod 700 "$HOME/horizon-signing"; if [ -e "$HOME/horizon-signing/horizon-updates.keystore" ]; then echo "Existing signing key preserved; not overwriting."; else keytool -genkeypair -keystore "$HOME/horizon-signing/horizon-updates.keystore" -alias androiddebugkey -keyalg RSA -keysize 3072 -validity 10000 -storepass android -keypass android -dname "CN=Horizon Android by Vanich" -noprompt >/dev/null 2>&1; fi; chmod 600 "$HOME/horizon-signing/horizon-updates.keystore"; base64 -w 0 "$HOME/horizon-signing/horizon-updates.keystore" > "$HOME/horizon-signing/horizon-key.txt"; chmod 600 "$HOME/horizon-signing/horizon-key.txt"; echo "READY: use the file in /home/codespace/horizon-signing/horizon-key.txt as the GitHub secret; download and back up horizon-updates.keystore."
```

If the terminal prints READY, continue.

## 3. Add the GitHub Secret

In Codespaces, open the **Explorer** sidebar and use **File → Open File…** (Ctrl+P) to open `/home/codespace/horizon-signing/horizon-key.txt`. Copy the entire **single long Base64 line**. Do **not** commit, share, paste in an issue, or post it in chat.

In the repository's GitHub website, go to **Settings → Secrets and variables → Actions → New repository secret**:

- Name: `HORIZON_SIGNING_KEYSTORE_B64`
- Secret: paste the copied Base64 text
- Click **Add secret**

## 4. Back up the actual key

From Codespaces Explorer, find `/home/codespace/horizon-signing/horizon-updates.keystore`, right-click → **Download**, and save it securely in at least one protected backup location outside Codespaces. The private key is irreplaceable for update signing. Codespaces may be deleted automatically; do not rely on it as the only backup.

Do not use a public artifact or workflow log to export the private key.

## 5. Verify signing setup

Repository **Actions → Android test APK (no release) → Run workflow**. The workflow requires the secret and restores the same keystore on each run. Future releases must keep the same package name and increase Android `versionCode`.

**Important:** previously published APKs signed with a temporary per-build key (including v1.0.0) cannot be updated in place by APKs signed with this new key. Back up game worlds and settings before uninstalling the old APK. The first persistent-key release becomes the baseline for future in-place updates.

### Security caveat

The current compatibility build uses upstream's `androiddebugkey` alias and `android` passwords. The keystore bytes are still secret and must be kept private, but for stronger production security we should migrate the build scripts to a dedicated release signing configuration with custom secrets and passwords *before* the first permanent-key release.
