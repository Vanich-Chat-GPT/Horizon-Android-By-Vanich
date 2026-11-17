# Current engineering milestone — verified artifact transport

Branch milestone: artifact downloader source has been added after the first successful ARM64 debug build.

CI must verify these additions before they are treated as buildable:
- AndroidX WorkManager dependency and foreground notification path;
- Android 14+ user-initiated JobScheduler service;
- app-private staging, HTTP range/ETag resume, SHA-1 verification and atomic promotion;
- ARM64 JNI library remains packaged in the APK.

No in-game compatibility, physical-device behaviour, Java runtime, Microsoft authorization, or complete Minecraft installation is implied by a successful APK compile.
