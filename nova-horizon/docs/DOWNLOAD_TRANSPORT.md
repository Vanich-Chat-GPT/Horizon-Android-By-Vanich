# Official artifact transport

## Purpose and scope

This subsystem downloads one artifact whose URL, size and SHA-1 have already come from validated Mojang version metadata. It is not yet the complete Minecraft installer or a game launcher.

## Scheduling

- Android 14/API 34 and later: JobScheduler with setUserInitiated(true), explicitly scheduled from a user action. The job declares network use and estimated download bytes. The system owns its lifecycle notification.
- Android 8/API 26 through Android 13/API 33: WorkManager 2.12.0 with a network constraint, foreground notification and cancellation intent.
- Both routes call the same downloader and write into app-private noBackupFilesDir/nova-horizon/minecraft.

WorkManager 2.12.0 requires API 24+, which is below NOVA's current minSdk 26. Android 16 imposes JobScheduler quota considerations on long-running WorkManager foreground workers, hence the separate user-initiated transfer route for API 34+.

## File integrity and resume

1. Reject non-HTTPS sources, unapproved hosts, user-info, fragments, query strings and non-standard ports.
2. Reject path traversal and ensure the canonical destination stays inside the app-private Minecraft directory.
3. Check free space before transfer.
4. Existing destination files are reused only if both expected size and SHA-1 match.
5. Partial transfers use Range and If-Range only when a strong ETag was stored from the previous response. If the server does not provide a strong ETag, the partial file is discarded and a full transfer starts.
6. A resumed response must be HTTP 206 with a matching Content-Range, matching ETag and expected total size. A server returning a full HTTP 200 response restarts the file from byte zero.
7. Hash all bytes, including any accepted partial prefix. Reject overlong, short, or hash-mismatched files.
8. Flush the staging file with fsync, then atomically move it to the final path. A failed verification never promotes the partial file.

## Known gaps

- The installer does not yet create a full install plan from version rules and asset indexes.
- Java library rules and native classifiers are not fully resolved for Android/Bionic.
- Asset index objects are not yet expanded into individual downloads.
- There is not yet a full downloads screen observing all JobScheduler and WorkManager tasks.
- A controlled HTTP test server must cover redirects, range resume, weak/missing/mismatched ETags, 200 fallback, 206 range errors, 416, short/long body, checksum mismatch, low storage, cancellation and process restart.
- Physical-device background, Doze, notification permission and network handover tests remain pending.

No Minecraft game files are bundled in the APK. Only files authorized by the official metadata and account entitlement can be downloaded for the user's own installation.
