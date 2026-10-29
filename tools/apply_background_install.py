#!/usr/bin/env python3
"""Android foreground installation notifications with native Rust progress.
Overlay after v1.1.1; requires Android SDK 35 / Rust Android cross toolchain.
"""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
def patch(path, old, new):
    p = root / path
    data = p.read_text(encoding="utf-8")
    if data.count(old) != 1:
        raise RuntimeError(f"{path}: expected exactly one anchor, got {data.count(old)}: {old[:110]!r}")
    p.write_text(data.replace(old, new, 1), encoding="utf-8")

manifest = "packaging/android/AndroidManifest.xml"
patch(manifest, '    <uses-permission android:name="android.permission.INTERNET" />',
'''    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />''')
patch(manifest, '    <application android:label="Horizon Android"',
'''    <application android:label="Horizon Android"''')
patch(manifest, '''        <activity android:name="dev.horizon.android.HorizonActivity"''',
'''        <service android:name="dev.horizon.android.HorizonInstallService"
            android:exported="false" android:foregroundServiceType="dataSync" />
        <activity android:name="dev.horizon.android.HorizonActivity"''')
activity = "packaging/android/java/dev/horizon/android/HorizonActivity.java"
patch(activity, '    private native void nativeDocumentResult(int request, int result, String uri);',
'''    private native void nativeDocumentResult(int request, int result, String uri);

    /** Invoked from native launcher before starting an install worker. */
    public void startInstallService(String progressPath) {
        if (android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[] {
                android.Manifest.permission.POST_NOTIFICATIONS
            }, 4242);
        }
        android.content.Intent intent = new android.content.Intent(this, HorizonInstallService.class);
        intent.putExtra("progress_path", progressPath);
        try {
            if (android.os.Build.VERSION.SDK_INT >= 26) startForegroundService(intent);
            else startService(intent);
        } catch (RuntimeException failure) {
            android.util.Log.w("HorizonInstall", "Unable to start foreground notification", failure);
        }
    }''')
service = root / "packaging/android/java/dev/horizon/android/HorizonInstallService.java"
service.parent.mkdir(parents=True, exist_ok=True)
service.write_text(r'''package dev.horizon.android;

import android.app.*;
import android.content.*;
import android.os.*;
import java.io.*;

/**
 * Android notification owner for the native Rust installation thread.
 * A foreground service keeps the app process eligible to continue while its
 * activity is not visible. Force-stop / OS resource pressure are exceptions.
 */
public final class HorizonInstallService extends Service {
    private static final String CHANNEL = "horizon_install";
    private static final int ID = 7301;
    private Handler handler;
    private String progressPath;
    private boolean running;

    private final Runnable tick = new Runnable() {
        @Override public void run() {
            if (!running) return;
            try {
                String line;
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(new FileInputStream(progressPath), "UTF-8"))) {
                    line = reader.readLine();
                }
                if (line != null) {
                    String[] fields = line.split("\\|", 4);
                    if (fields.length == 4) {
                        String phase = fields[0];
                        long done = Long.parseLong(fields[1]);
                        long total = Long.parseLong(fields[2]);
                        String label = fields[3];
                        if ("D".equals(phase) || "E".equals(phase)) {
                            show(label, done, total, true);
                            running = false;
                            stopForeground(STOP_FOREGROUND_DETACH);
                            stopSelf();
                            return;
                        }
                        show(label, done, total, false);
                    }
                }
            } catch (IOException | NumberFormatException error) {
                // The worker may not have created the state file yet.
            }
            handler.postDelayed(this, 1000L);
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(
            CHANNEL, "Установка Minecraft", NotificationManager.IMPORTANCE_LOW));
        handler = new Handler(Looper.getMainLooper());
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent == null || !intent.hasExtra("progress_path")) {
            stopSelf();
            return START_NOT_STICKY;
        }
        progressPath = intent.getStringExtra("progress_path");
        running = true;
        Notification n = notification("Подготовка Minecraft", 0, 0, false);
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(ID, n, android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        } else {
            startForeground(ID, n);
        }
        handler.removeCallbacks(tick);
        handler.post(tick);
        return START_NOT_STICKY;
    }

    private Notification notification(String message, long done, long total, boolean finished) {
        Intent open = new Intent(this, HorizonActivity.class);
        PendingIntent pending = PendingIntent.getActivity(this, 0, open,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder b = new Notification.Builder(this, CHANNEL)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(finished ? "HorizonCraft — установка" : "HorizonCraft — скачивание")
            .setContentText(message)
            .setContentIntent(pending)
            .setOnlyAlertOnce(true)
            .setOngoing(!finished);
        if (!finished) {
            if (total > 0) {
                int percent = (int)Math.min(100L, done * 100L / total);
                b.setProgress(100, percent, false);
                b.setSubText(String.format(java.util.Locale.ROOT,
                    "%.1f / %.1f MiB", done / 1048576.0, total / 1048576.0));
            } else {
                b.setProgress(0, 0, true);
            }
        } else {
            b.setSmallIcon(android.R.drawable.stat_sys_download_done);
            b.setAutoCancel(true);
        }
        return b.build();
    }

    private void show(String message, long done, long total, boolean finished) {
        getSystemService(NotificationManager.class).notify(
            ID, notification(message, done, total, finished));
    }

    @Override public void onDestroy() {
        running = false;
        if (handler != null) handler.removeCallbacks(tick);
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent intent) { return null; }
}
''', encoding="utf-8")

platform = "crates/horizon-client/src/android/platform.rs"
patch(platform, 'use std::cell::RefCell;',
'''use std::cell::RefCell;

/// Start a foreground Android service while the Activity is in the foreground.
/// The service keeps the process alive when the Activity closes, and reads the
/// native worker's atomic progress file every second.
pub(super) fn start_install_service(progress_file: &std::path::Path) {
    crate::APP.with(|slot| {
        let app = slot.borrow();
        let Some(app) = app.as_ref() else { return };
        let Ok(vm) = (unsafe { JavaVM::from_raw(app.vm_as_ptr().cast()) }) else { return };
        let Ok(mut env) = vm.attach_current_thread() else { return };
        let activity = unsafe { JObject::from_raw(app.activity_as_ptr().cast()) };
        let path = progress_file.to_string_lossy();
        if let Ok(text) = env.new_string(path.as_ref()) {
            let arg = JObject::from(text);
            if let Err(e) = env.call_method(&activity, "startInstallService",
                "(Ljava/lang/String;)V", &[JValue::Object(&arg)]) {
                log::warn!("Could not start install notification: {e}");
            }
        }
        std::mem::forget(activity); // The AndroidApp owns the JNI activity ref.
    });
}
''')

launcher = "crates/horizon-client/src/android/launcher.rs"
patch(launcher, '''            let install = self.install.clone();
            let (sender, receiver) = mpsc::channel();''',
'''            let install = self.install.clone();
            let status_path = home.join(".horizon-install-status");
            let _ = std::fs::write(&status_path, "P|0|0|Подготовка Minecraft");
            crate::platform::start_install_service(&status_path);
            let (sender, receiver) = mpsc::channel();''')
patch(launcher, '''            std::thread::spawn(move || {
                let result =
                    horizon_client::official_install::install_with_progress(&home, |update| {
                        let mut current = install.lock().unwrap();''',
'''            std::thread::spawn(move || {
                let last_write = std::sync::Mutex::new(std::time::Instant::now()
                    - std::time::Duration::from_secs(2));
                let result =
                    horizon_client::official_install::install_with_progress(&home, |update| {
                        // Throttle disk writes; the UI reads the in-memory atomic data.
                        if let Ok(mut last) = last_write.lock() {
                            if last.elapsed() >= std::time::Duration::from_millis(750) {
                                let label = match update.stage {
                                    horizon_client::official_install::InstallStage::Download
                                        => "Скачивание ресурсов",
                                    horizon_client::official_install::InstallStage::Extract
                                        => "Распаковка файлов",
                                    horizon_client::official_install::InstallStage::WorldData
                                        => "Подготовка данных мира",
                                    horizon_client::official_install::InstallStage::Controls
                                        => "Загрузка управления",
                                    horizon_client::official_install::InstallStage::Finalize
                                        => "Завершение установки",
                                    _ => "Проверка Minecraft",
                                };
                                let temp = status_path.with_extension("tmp");
                                if std::fs::write(&temp, format!(
                                    "P|{}|{}|{}", update.done, update.total, label
                                )).is_ok() {
                                    let _ = std::fs::rename(&temp, &status_path);
                                }
                                *last = std::time::Instant::now();
                            }
                        }
                        let mut current = install.lock().unwrap();''')
patch(launcher, '''                let _ = sender.send(result.map_err(|e| e.to_string()));
            });''',
'''                let message = if result.is_ok() {
                    "D|1|1|Установка Minecraft завершена".to_owned()
                } else {
                    "E|0|0|Ошибка установки Minecraft".to_owned()
                };
                let temp = status_path.with_extension("tmp");
                if std::fs::write(&temp, message).is_ok() {
                    let _ = std::fs::rename(&temp, &status_path);
                }
                let _ = sender.send(result.map_err(|e| e.to_string()));
            });''')
print("Added Android foreground installation notification service + native progress bridge.")
