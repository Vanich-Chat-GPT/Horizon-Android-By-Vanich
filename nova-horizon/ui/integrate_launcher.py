#!/usr/bin/env python3
"""Integrate the NOVA HORIZON home screen and requested Android defaults into the pinned port."""
from pathlib import Path
import json
import shutil
import sys

def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one patch anchor, found {count}: {old[:100]!r}")
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

def add_translations(path: Path, values: dict[str, str]) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(values)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: integrate_launcher.py <upstream checkout>")
    root = Path(sys.argv[1]).resolve()
    android = root / "packaging/android"
    java_dir = android / "java/io/github/juanluci/starling"
    activity = java_dir / "LauncherActivity.java"

    # Add the NOVA home screen source; build_apk.py compiles every Java source in this directory.
    home_source = Path(__file__).with_name("LauncherHome.java")
    if not home_source.is_file():
        raise SystemExit(f"Missing NOVA launcher UI source: {home_source}")
    shutil.copyfile(home_source, java_dir / "LauncherHome.java")

    # The ongoing Android notification reports the measured receive rate for this app UID.
    work_service = java_dir / "WorkService.java"
    work_service.write_text("""package dev.nova.horizon;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.net.TrafficStats;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.Process;
import android.os.SystemClock;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

public final class WorkService extends Service {
    private static final String CHANNEL = "work";
    private static final int NOTIFICATION = 1;
    private static final Map<String, String> REASONS = new LinkedHashMap<>();

    private final Handler handler = new Handler(Looper.getMainLooper());
    private long lastRxBytes = -1;
    private long lastSampleMs;
    private boolean speedLoop;

    private final Runnable speedUpdate = new Runnable() {
        @Override public void run() {
            if (!hasReasons()) {
                speedLoop = false;
                stopForeground(true);
                stopSelf();
                return;
            }
            long now = SystemClock.elapsedRealtime();
            long bytes = TrafficStats.getUidRxBytes(Process.myUid());
            String content = line();
            if (bytes >= 0 && lastRxBytes >= 0 && lastSampleMs > 0 && now > lastSampleMs) {
                long received = Math.max(0, bytes - lastRxBytes);
                double mbPerSecond = received * 1000.0 / (now - lastSampleMs) / 1_000_000.0;
                content += String.format(Locale.US, "  ·  %.1f MB/s", mbPerSecond);
            }
            lastRxBytes = bytes;
            lastSampleMs = now;
            NotificationManager manager =
                    (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) manager.notify(NOTIFICATION, buildNotification(content));
            handler.postDelayed(this, 1000);
        }
    };

    static void hold(Context context, String reason, String line, boolean on) {
        boolean running;
        synchronized (REASONS) {
            if (on) {
                REASONS.remove(reason);
                REASONS.put(reason, line);
            } else {
                REASONS.remove(reason);
            }
            running = !REASONS.isEmpty();
        }
        Intent intent = new Intent(context, WorkService.class);
        try {
            if (running) {
                if (Build.VERSION.SDK_INT >= 26) context.startForegroundService(intent);
                else context.startService(intent);
            } else {
                context.startService(intent);
            }
        } catch (RuntimeException ignored) {
            // Android may refuse a foreground service started from the background.
        }
    }

    private static boolean hasReasons() {
        synchronized (REASONS) { return !REASONS.isEmpty(); }
    }

    private static String line() {
        synchronized (REASONS) {
            String last = "NOVA HORIZON выполняет задачу";
            for (String value : REASONS.values()) last = value;
            return last;
        }
    }

    private Notification buildNotification(String content) {
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(this, CHANNEL)
                : new Notification.Builder(this);
        return builder.setSmallIcon(getApplicationInfo().icon)
                .setContentTitle(getString(R.string.work_title))
                .setContentText(content)
                .setOngoing(true)
                .build();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationManager manager =
                    (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) {
                manager.createNotificationChannel(new NotificationChannel(
                        CHANNEL, getString(R.string.work_channel), NotificationManager.IMPORTANCE_LOW));
            }
        }
        try {
            Notification notification = buildNotification(line());
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(NOTIFICATION, notification,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
            } else {
                startForeground(NOTIFICATION, notification);
            }
        } catch (RuntimeException e) {
            stopSelf();
            return START_NOT_STICKY;
        }
        if (!hasReasons()) {
            handler.removeCallbacks(speedUpdate);
            speedLoop = false;
            stopForeground(true);
            stopSelfResult(startId);
        } else if (!speedLoop) {
            lastRxBytes = TrafficStats.getUidRxBytes(Process.myUid());
            lastSampleMs = SystemClock.elapsedRealtime();
            speedLoop = true;
            handler.postDelayed(speedUpdate, 1000);
        }
        return START_NOT_STICKY;
    }

    @Override
    public void onDestroy() {
        handler.removeCallbacks(speedUpdate);
        speedLoop = false;
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
}
""", encoding="utf-8")

    replace_once(
        activity,
        "public final class LauncherActivity extends Activity {",
        "public final class LauncherActivity extends Activity implements LauncherHome.Actions {",
    )
    replace_once(
        activity,
        """        } else {
            play();
        }
    }

    private void play() {""",
        """        } else {
            getWindow().setStatusBarColor(0xFF080B17);
            getWindow().setNavigationBarColor(0xFF080B17);
            setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
            setContentView(LauncherHome.create(this, this));
        }
    }

    @Override
    public void play() {""",
    )

    callbacks = """
    @Override
    public void diagnostics() {
        startActivity(new Intent(this, DiagnosticsActivity.class));
    }

    @Override
    public void settings() {
        // The Rust client's graphics, input and audio settings remain the source of truth.
        play();
    }

    @Override
    public void info() {
        new AlertDialog.Builder(this)
                .setTitle("О NOVA HORIZON")
                .setMessage("Minecraft Java Edition 26.3, нативный Rust-клиент Horizon. "
                        + "Для установки игровых файлов нужна собственная копия Minecraft Java Edition.")
                .setPositiveButton("Понятно", null)
                .show();
    }

    @Override
    public void pick(String kind) {
        Intent picker = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        picker.addCategory(Intent.CATEGORY_OPENABLE);
        picker.setType("*/*");
        picker.putExtra(Intent.EXTRA_MIME_TYPES, new String[] {
                "application/zip", "application/x-zip-compressed", "application/octet-stream"
        });
        String title = "Выберите файл для импорта";
        if ("mods".equals(kind)) title = "Выберите мод или модпак";
        else if ("resources".equals(kind)) title = "Выберите ресурспак";
        else if ("shaders".equals(kind)) title = "Выберите shader pack";
        picker.putExtra(Intent.EXTRA_TITLE, title);
        try {
            startActivityForResult(picker, 4);
        } catch (Exception error) {
            new AlertDialog.Builder(this)
                    .setMessage("Не удалось открыть выбор файла: " + error.getMessage())
                    .setPositiveButton("OK", null)
                    .show();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != 4 || resultCode != RESULT_OK || data == null || data.getData() == null) {
            return;
        }
        final AlertDialog copying = new AlertDialog.Builder(this)
                .setMessage("Импортирую файл…")
                .setCancelable(false)
                .show();
        receive(this, data.getData(), new Runnable() {
            @Override
            public void run() {
                copying.dismiss();
                play();
            }
        });
    }

"""
    replace_once(
        activity,
        "    /**\n     * While the game starts again (a world whose mods are not the running ones):",
        callbacks + "    /**\n     * While the game starts again (a world whose mods are not the running ones):",
    )

    manifest = android / "AndroidManifest.xml"
    replace_once(manifest, 'android:noHistory="true"', "")
    replace_once(
        manifest,
        'android:theme="@android:style/Theme.Translucent.NoTitleBar">',
        'android:screenOrientation="sensorLandscape"\n            android:theme="@android:style/Theme.Material.NoActionBar">',
    )

    build = android / "build_apk.py"
    replace_once(
        build,
        '    zip_folder(HERE.parent / "lowbudget" / "pack", folder / "lowbudget.zip")',
        '    shutil.copyfile(ROOT / "docs/media/night.webp", folder / "launcher-bg.webp")\n'
        '    zip_folder(HERE.parent / "lowbudget" / "pack", folder / "lowbudget.zip")',
    )

    releases = root / "crates/horizon-client/src/starling_releases.rs"
    replace_once(
        releases,
        'pub const REPOSITORIES: [&str; 2] = ["starling-client/starling", "JuanLuci/starling"];',
        'pub const REPOSITORIES: [&str; 1] = ["Vanich-Chat-GPT/Horizon-Android-By-Vanich"];',
    )
    replace_once(
        releases,
        'let name = format!("starling-{version}-{abi}.apk");',
        'let name = format!("NOVA-HORIZON-{version}-{abi}.apk");',
    )
    old_update_test = """    #[test]
    fn only_starlings_own_apk_is_an_update() {
        // Horizon Android's last release, the organisation's latest today: not Starling's.
        let horizon =
            json!({"tag_name": "v0.7.8", "assets": [asset("Horizon-Android-0.7.8-arm64-v8a.apk")]});
        assert_eq!(update_for_abi(&horizon, "0.2.2", "arm64-v8a"), None);
        // A preview build is another app, signed with another key.
        let preview = json!({"tag_name": "v0.8.0", "assets": [asset("starling-preview-0.8.0-arm64-v8a.apk")]});
        assert_eq!(update_for_abi(&preview, "0.2.2", "arm64-v8a"), None);
        let release = json!({"tag_name": "v0.8.0", "assets": [
            asset("starling-preview-0.8.0-arm64-v8a.apk"),
            asset("StarlingVisuals.zip"),
            asset("starling-0.8.0-arm64-v8a.apk"),
        ]});
        let update = update_for_abi(&release, "0.2.2", "arm64-v8a").unwrap();
        assert_eq!(update.version, "0.8.0");
        assert_eq!(update.name, "starling-0.8.0-arm64-v8a.apk");
        assert_eq!(update.sha256.as_deref(), Some("ab"));
        assert_eq!(
            update_for_abi(&release, "0.8.0", "arm64-v8a"),
            None,
            "not newer"
        );
    }"""
    new_update_test = """    #[test]
    fn only_nova_horizon_arm64_apk_is_an_update() {
        let unrelated = json!({"tag_name": "v3.0.0", "assets": [asset("Horizon-Android-3.0.0-arm64-v8a.apk")]});
        assert_eq!(update_for_abi(&unrelated, "2.9.9", "arm64-v8a"), None);
        let preview = json!({"tag_name": "v3.0.0", "assets": [asset("NOVA-HORIZON-preview-3.0.0-arm64-v8a.apk")]});
        assert_eq!(update_for_abi(&preview, "2.9.9", "arm64-v8a"), None);
        let release = json!({"tag_name": "v3.0.0", "assets": [
            asset("NOVA-HORIZON-preview-3.0.0-arm64-v8a.apk"),
            asset("StarlingVisuals.zip"),
            asset("NOVA-HORIZON-3.0.0-arm64-v8a.apk"),
        ]});
        let update = update_for_abi(&release, "2.9.9", "arm64-v8a").unwrap();
        assert_eq!(update.version, "3.0.0");
        assert_eq!(update.name, "NOVA-HORIZON-3.0.0-arm64-v8a.apk");
        assert_eq!(update.sha256.as_deref(), Some("ab"));
        assert_eq!(update_for_abi(&release, "3.0.0", "arm64-v8a"), None, "not newer");
    }"""
    replace_once(releases, old_update_test, new_update_test)

    update_offer = root / "crates/horizon-client/src/game/update_offer.rs"
    old_offer = """        let (title, body, buttons): (String, String, &[&str]) = match &stage {
            Stage::Ask => (
                format!("Starling {version} is out"),
                format!(
                    "Update now? Starling downloads it ({} MB) and Android installs it over this \\
                     one: your worlds and settings stay.",
                    mb(release.size)
                ),
                &["Update", "Tomorrow", "No"],
            ),
            Stage::Downloading => (
                format!("Downloading Starling {version}"),
                format!("{} of {} MB", mb(done), mb(total)),
                &["Cancel"],
            ),
            Stage::Installing => (
                format!("Install Starling {version}"),
                "Android asks to install the update (the first time, to allow installs from \\
                 Starling). Once it is in, open Starling again."
                    .into(),
                &["Install", "Later"],
            ),
            Stage::Failed(e) => (
                "The update did not download".into(),
                e.clone(),
                &["Try again", "Later"],
            ),
        };"""
    new_offer = """        let (title, body, buttons): (String, String, Vec<String>) = match &stage {
            Stage::Ask => (
                crate::lang::get("starling.update.ask.title").replace("{version}", version),
                crate::lang::get("starling.update.ask.body").replace("{size}", &mb(release.size)),
                vec![
                    crate::lang::get("starling.update.button.update"),
                    crate::lang::get("starling.update.button.tomorrow"),
                    crate::lang::get("starling.update.button.no"),
                ],
            ),
            Stage::Downloading => (
                crate::lang::get("starling.update.download.title").replace("{version}", version),
                crate::lang::get("starling.update.download.body")
                    .replace("{done}", &mb(done))
                    .replace("{total}", &mb(total)),
                vec![crate::lang::get("starling.update.button.cancel")],
            ),
            Stage::Installing => (
                crate::lang::get("starling.update.install.title").replace("{version}", version),
                crate::lang::get("starling.update.install.body"),
                vec![
                    crate::lang::get("starling.update.button.install"),
                    crate::lang::get("starling.update.button.later"),
                ],
            ),
            Stage::Failed(e) => (
                crate::lang::get("starling.update.failed.title"),
                e.clone(),
                vec![
                    crate::lang::get("starling.update.button.retry"),
                    crate::lang::get("starling.update.button.later"),
                ],
            ),
        };"""
    replace_once(update_offer, old_offer, new_offer)

    # Static joystick is the first-run default; the user can still choose Follow Finger.
    layout = root / "crates/horizon-client-render/src/android_controls/layout.rs"
    replace_once(
        layout,
        """    /// Joystick stays in its fixed absolute placement.
    AbsoluteFixed,
    /// Floating joystick center follows the finger where touched.
    #[default]
    FollowFinger,""",
        """    /// Joystick stays in its fixed absolute placement.
    #[default]
    AbsoluteFixed,
    /// Floating joystick center follows the finger where touched.
    FollowFinger,""",
    )
    replace_once(
        layout,
        "            move_area: JoystickMoveArea::FollowFinger,",
        "            move_area: JoystickMoveArea::AbsoluteFixed,",
    )

    # New Android profiles start in Russian; existing saved language choices remain untouched.
    settings = root / "crates/horizon-client-render/src/settings.rs"
    replace_once(settings, '            language: "en_us".into(),', '            language: "ru_ru".into(),')

    # Expose a clear, localized static/floating selector in the control hub.
    control_ui = root / "crates/horizon-client/src/android_control_ui.rs"
    replace_once(
        control_ui,
        "                let area_lbl = settings.joystick_style.move_area.label();",
        """                let area_lbl = match settings.joystick_style.move_area {
                    crate::android_controls::JoystickMoveArea::AbsoluteFixed =>
                        crate::lang::get("starling.controls.joystick_static"),
                    crate::android_controls::JoystickMoveArea::FollowFinger =>
                        crate::lang::get("starling.controls.joystick_floating"),
                    crate::android_controls::JoystickMoveArea::MidBottomLeft =>
                        crate::lang::get("starling.controls.joystick_mid_bottom_left"),
                    crate::android_controls::JoystickMoveArea::RightSideAnywhere =>
                        crate::lang::get("starling.controls.joystick_right_side"),
                };""",
    )
    replace_once(
        control_ui,
        '                    "Joystick Active Zone",',
        '                    &crate::lang::get("starling.controls.joystick_mode"),',
    )
    replace_once(
        control_ui,
        "                    area_lbl,",
        "                    &area_lbl,",
    )

    # The Redmi Pad SE 8.7 has a 90 Hz panel. Keep near-field image quality intact,
    # cap at the panel rate, and spend the quality/performance trade-off on far terrain.
    graphics = root / "crates/horizon-client-render/src/graphics.rs"
    old_mobile = """/// A phone's first start: settings for its tier instead of the desktop's (measured on a
/// Snapdragon 8 Gen 2 at 3200x1440; slower tiers scaled down from it).
///
/// The frame cap is 60: a steady 60 runs cooler than 70 to 90 that dips, and the display
/// follows the cap. Mobs think on the render thread, so the simulation distance stays short:
/// at 12 the ticks of a few hundred mobs made every third frame late. Clouds cost the GPU
/// 1.7 ms of a frame at any distance, fancy leaves are overdraw on tiled GPUs, and animated
/// textures are mixed on the CPU each frame.
pub fn apply_mobile_defaults(tier: crate::system_stats::Tier, s: &mut crate::settings::Settings) {
    use crate::system_stats::Tier;
    let high = tier == Tier::High;
    // A fast phone is not held at 60 frames: an uncapped frame rate lets its display run at its
    // own rate, and the frame cap stays the player's choice (Options, or `maxFps`).
    s.max_fps = if high { 260 } else { 60 };
    s.render_distance = match tier {
        Tier::High => 10,
        Tier::Mid => 8,
        Tier::Low => 6,
    };
    s.simulation_distance = if high { 8 } else { 6 };
    s.clouds = if high { "fast" } else { "false" }.into();
    s.particles = if high { 1 } else { 2 };
    s.entity_shadows = high;
    s.biome_blend = if high { 1 } else { 0 };
    s.mipmap_levels = if high { 4 } else { 2 };
    s.entity_distance = match tier {
        Tier::High => 1.0,
        Tier::Mid => 0.75,
        Tier::Low => 0.5,
    };
    s.cutout_leaves = high;
    s.weather_radius = if high { 5 } else { 3 };
    // Bedrock's touch default: the stick walks up a block without the jump button.
    s.auto_jump = true;
    s.graphics_preset = "custom".into();
    let g = &mut s.horizon;
    g.preset = Preset::Custom;
    g.resolution_scale = match tier {
        Tier::High => 100,
        Tier::Mid => 85,
        Tier::Low => 70,
    };
    g.animated_textures = tier != Tier::Low;
    // A phone's GPU is an integrated one, which far terrain slows most.
    g.far_detail = if high {
        FarDetail::Full
    } else {
        FarDetail::Reduced
    };
    // VSync is what holds a fast phone at its display's rate and hides the frame rate the GPU
    // can make: off by default, as the frame cap already keeps the GPU from running flat out.
    s.vsync = false;
}"""
    new_mobile = """/// Mobile defaults tuned for NOVA HORIZON: 90 FPS ceiling, full-resolution near
/// terrain and normal vanilla effects. Lower tiers trade only far-terrain detail and
/// simulation/render distance, rather than blurring the whole frame or disabling effects.
pub fn apply_mobile_defaults(tier: crate::system_stats::Tier, s: &mut crate::settings::Settings) {
    use crate::system_stats::Tier;
    let high = tier == Tier::High;
    s.max_fps = 90;
    s.render_distance = match tier {
        Tier::High => 12,
        Tier::Mid => 10,
        Tier::Low => 8,
    };
    s.simulation_distance = if high { 8 } else { 6 };
    s.clouds = "true".into();
    s.particles = 0;
    s.entity_shadows = true;
    s.biome_blend = 2;
    s.mipmap_levels = 4;
    s.entity_distance = 1.0;
    s.cutout_leaves = true;
    s.weather_radius = 10;
    // Bedrock's touch default: the stick walks up a block without the jump button.
    s.auto_jump = true;
    s.graphics_preset = "custom".into();
    let g = &mut s.horizon;
    g.preset = Preset::Custom;
    g.resolution_scale = 100;
    g.animated_textures = true;
    g.far_detail = if high {
        FarDetail::Full
    } else {
        FarDetail::Reduced
    };
    // Let the 90 FPS cap govern frame pacing rather than double-throttling with VSync.
    s.vsync = false;
}"""
    replace_once(graphics, old_mobile, new_mobile)
    old_test = """    #[test]
    fn phones_start_lighter_by_tier() {
        use crate::system_stats::Tier;
        let mut low = crate::settings::Settings::default();
        apply_mobile_defaults(Tier::Low, &mut low);
        let mut high = crate::settings::Settings::default();
        apply_mobile_defaults(Tier::High, &mut high);
        assert_eq!((low.max_fps, high.max_fps), (60, 260));
        assert!(low.render_distance < high.render_distance);
        assert_eq!(
            (low.clouds.as_str(), high.clouds.as_str()),
            ("false", "fast")
        );
        assert!(low.horizon.resolution_scale < high.horizon.resolution_scale);
        assert!(!low.horizon.animated_textures && high.horizon.animated_textures);
        // Auto-Jump on, as on Bedrock's touch screens.
        assert!(low.auto_jump && high.auto_jump);
        // What the options screens read back.
        let file = high.to_file();
        let back = crate::settings::Settings::from_file(file);
        assert_eq!(back.render_distance, 10);
        assert!(back.auto_jump);
    }"""
    new_test = """    #[test]
    fn mobile_defaults_keep_nearby_quality_and_cap_at_90_fps() {
        use crate::system_stats::Tier;
        let mut low = crate::settings::Settings::default();
        apply_mobile_defaults(Tier::Low, &mut low);
        let mut high = crate::settings::Settings::default();
        apply_mobile_defaults(Tier::High, &mut high);
        assert_eq!((low.max_fps, high.max_fps), (90, 90));
        assert_eq!((low.render_distance, high.render_distance), (8, 12));
        assert_eq!((low.clouds.as_str(), high.clouds.as_str()), ("true", "true"));
        assert_eq!((low.horizon.resolution_scale, high.horizon.resolution_scale), (100, 100));
        assert!(low.horizon.animated_textures && high.horizon.animated_textures);
        assert_eq!(low.particles, 0);
        assert!(low.entity_shadows && low.cutout_leaves);
        assert_eq!(low.mipmap_levels, 4);
        assert_eq!(low.horizon.far_detail, FarDetail::Reduced);
        assert_eq!(high.horizon.far_detail, FarDetail::Full);
        // Auto-Jump on, as on Bedrock's touch screens.
        assert!(low.auto_jump && high.auto_jump);
        // What the options screens read back.
        let file = high.to_file();
        let back = crate::settings::Settings::from_file(file);
        assert_eq!(back.render_distance, 12);
        assert_eq!(back.max_fps, 90);
        assert!(back.auto_jump);
    }"""
    replace_once(graphics, old_test, new_test)

    add_translations(
        root / "crates/horizon-client/assets/horizon/lang/en_us.json",
        {
            "starling.ui.touch_controls": "Touch Controls",
            "starling.controls.joystick_mode": "Joystick mode",
            "starling.controls.joystick_static": "Static joystick",
            "starling.controls.joystick_floating": "Floating joystick",
            "starling.controls.joystick_mid_bottom_left": "Mid-bottom left",
            "starling.controls.joystick_right_side": "Right side",
            "starling.update.ask.title": "NOVA HORIZON {version} is available",
            "starling.update.ask.body": "Update now? NOVA HORIZON will download it ({size} MB), then Android installs it over this version. Your worlds and settings stay.",
            "starling.update.download.title": "Downloading NOVA HORIZON {version}",
            "starling.update.download.body": "{done} of {total} MB",
            "starling.update.install.title": "Install NOVA HORIZON {version}",
            "starling.update.install.body": "Android will ask to install the update. The first time, allow installs from NOVA HORIZON. Open NOVA HORIZON again when it finishes.",
            "starling.update.failed.title": "The update did not download",
            "starling.update.button.update": "Update",
            "starling.update.button.tomorrow": "Tomorrow",
            "starling.update.button.no": "No",
            "starling.update.button.cancel": "Cancel",
            "starling.update.button.install": "Install",
            "starling.update.button.later": "Later",
            "starling.update.button.retry": "Try again",
        },
    )
    ru_path = root / "crates/horizon-client/assets/horizon/lang/ru_ru.json"
    base_path = Path(__file__).with_name("ru_ru_base.json")
    base = json.loads(base_path.read_text(encoding="utf-8"))
    current_ru = json.loads(ru_path.read_text(encoding="utf-8"))
    merged_ru = dict(base)
    merged_ru.update(current_ru)
    merged_ru.update({
        "horizon.options.server_stick": "Джойстик на серверах",
        "horizon.options.server_stick.tooltip": "Режим движения джойстика на серверах. Java передаёт движение клавишами, поэтому античит может возвращать игрока назад, если скорость или угол аналогового стика не совпадают с ожидаемыми. Аналоговый режим передаёт наклон стика; свободное направление сохраняет полный ход под любым углом; крестовина использует восемь направлений. Если сервер уже выбрал режим после отката, изменить его можно здесь во время игры.",
        "horizon.options.stick_prompt": "Спрашивать при откате",
        "horizon.options.stick_prompt.tooltip": "Если сервер возвращает вас назад при движении джойстиком, предложить изменить режим управления.",
        "horizon.server_stick.analog": "Аналоговый",
        "horizon.server_stick.free": "Свободное направление",
        "horizon.server_stick.keys": "Крестовина (8 направлений)",
        "starling.stick_prompt.title": "Сервер возвращает вас назад",
        "starling.stick_prompt.body": "Античит сервера (Grim или аналогичный) принимает только движения, созданные клавишами Java. Выберите режим джойстика для этого сервера; изменить его можно в настройках управления.",
        "starling.stick_prompt.free": "Свободное направление (любой угол, полная скорость)",
        "starling.stick_prompt.keys": "Крестовина (8 направлений, полная скорость)",
        "starling.stick_prompt.analog": "Оставить аналоговый режим",
        "starling.stick_prompt.remember": "Запомнить для этого сервера",
        "starling.stick_prompt.dont_ask": "Больше не спрашивать",
        "Sets distance, particles, shadows, sky and fog; changing one makes it Custom.": "Настраивает дальность, частицы, тени, небо и туман; изменение любого параметра включает пользовательский режим.",
        "Full Stats": "Полная статистика",
        "Shortcut: %s": "Сочетание клавиш: %s",
        "A key that opens this screen from the game. Not bound at first.": "Клавиша для открытия этого экрана из игры. Изначально не назначена.",
        "horizon.extras.wheel_cycles_settings.tooltip": "Колесо мыши над параметром меняет его значение, как в оригинальной игре. В выключенном состоянии колесо только прокручивает список.",
        "starling.account.setup.horizon.title": "Переходите с Horizon Android?",
        "starling.account.setup.horizon.body": "Ваши миры и наборы ресурсов можно перенести. Сообщение сверху покажет, что было добавлено. Нажмите «Далее», когда перенос завершится.",
        "starling.account.setup.horizon.bring": "Перенести данные",
        "starling.account.setup.horizon.pick": "Выбрать папку ещё раз",
        "starling.account.setup.skip": "Пропустить",
        "starling.account.setup.next": "Далее",
        "starling.account.setup.retry": "Повторить",
        "starling.account.setup.fish": "Продолжить",
        "starling.account.setup.settings": "Настройки",
        "starling.account.setup.offline.title": "Вы уверены?",
        "starling.account.setup.offline.body": "Без входа в аккаунт большинство серверов будет недоступно. Рекомендуем войти через Microsoft.",
        "starling.account.setup.code.title": "Вход через Microsoft",
        "starling.account.setup.code.body": "На сайте {link} введите этот код:",
        "starling.account.setup.download.title": "Загрузка игры",
        "starling.account.setup.download.body": "Файлы загружены с зеркала и проверены по отдельности.",
        "starling.account.setup.download.progress": "{files} из {total} файлов, {done} из {size} МБ",
        "starling.account.setup.download.checking": "Проверка файлов",
        "starling.account.setup.java.title": "Подготовка игры",
        "starling.account.setup.java.body": "Загружаем Java для подготовки игровых файлов.",
        "starling.account.setup.unpacking.body": "Распаковка Java.",
        "starling.account.setup.preparing.body": "Это займёт несколько минут. Не закрывайте NOVA HORIZON.",
        "starling.account.setup.done.title": "Игра готова",
        "starling.account.setup.done.body": "Игровые файлы подготовлены.",
        "starling.account.setup.failed.title": "Не удалось завершить подготовку",
        "starling.dedicated.button": "Запустить как сервер…",
        "starling.shaderpacks.folder": "Папка",
        "starling.shaderpacks.private": "В файлах приложения: нажмите «Открыть папку наборов», чтобы перейти к ним",
        "starling.shaderpacks.note": "Собственные наборы Horizon, а также наборы Iris и OptiFine",
        "starling.ui.choose_file": "Выбрать файл…",
        "starling.ui.shader_packs": "Наборы шейдеров…",
        "starling.ui.touch_controls": "Сенсорное управление",
        "starling.ui.bedrock_inventory": "Инвентарь Bedrock: ",
        "starling.ui.customize_layout": "Настроить раскладку…",
        "starling.ui.customize_touch": "Настроить сенсорное управление и GoyControl…",
        "starling.ui.delete": "Удалить",
        "starling.ui.add_button": "Добавить кнопку",
        "starling.ui.draw_or_import": "Нарисовать или импортировать…",
        "starling.ui.no_icon": "Без значка: показывать название",
        "starling.ui.name": "Название",
        "starling.ui.movement_look_sensitivity": "Чувствительность движения и обзора",
        "starling.ui.control_hub_feedback": "Центр управления и обратная связь",
        "starling.ui.hud_buttons_layout": "Кнопки HUD и раскладка",
        "starling.ui.joystick_actions_gyroscope": "Джойстик, действия и гироскоп",
        "starling.ui.settings_of_the_pack_on": "Настройки набора включены",
        "starling.ui.sends_a_command_or_a_chat_line_when_pres": "Отправляет команду /… или сообщение в чат при нажатии",
        "starling.ui.or_holds_a_key_while_pressed": "Или удерживает клавишу, пока кнопка нажата",
        "starling.ui.how_it_looks": "Внешний вид",
        "starling.ui.while_pressed": "При удержании",
        "starling.ui.buttons_of_your_own_place_them_in_touch_": "Свои кнопки: разместите их в разделе «Сенсорное управление»",
        "starling.ui.your_name_in_worlds_and_on_servers_from_": "Ваше имя в мирах и на серверах, начиная со следующего запуска",
        "starling.ui.no_skins_yet_put_64x64_pngs_in_the_skins": "Скинов пока нет: поместите PNG 64×64 в папку skins",
        "starling.ui.only_you_see_this_skin_on_a_server_other": "Этот скин виден только вам. На сервере остальные игроки видят",
        "starling.ui.compile": "Скомпилировать",
        "starling.ui.play_without_native_mods": "Играть без нативных модов",
        "starling.ui.use_github_slower": "Использовать GitHub (медленнее)",
        "starling.ui.zooms_in": "Приближает изображение.",
        "starling.ui.zoom_key": "Клавиша приближения",
        "starling.ui.may_show_hud_panels": "Может отображать панели HUD.",
        "starling.ui.invalid_package": "Недопустимый пакет",
        "starling.ui.mojang_said_no": "Mojang отклонила запрос",
        "starling.ui.waiting_for_an_agent": "Ожидание агента.",
        "starling.ui.select_mods_and_data_packs": "Выбрать моды и наборы данных",
        "starling.ui.confirm": "Подтвердить",
        "starling.ui.use_this_pack": "Использовать этот набор?",
        "starling.ui.packs": "Наборы",
        "starling.ui.done": "Готово",
        "starling.ui.graphics_api_prefer_vulkan_experimental": "Графический API: предпочитать Vulkan (экспериментально)",
        "starling.ui.items": "Предметы",
        "starling.ui.open": "Открыть?",
        "starling.ui.customize": "Настроить…",
        "starling.ui.lobby": "Лобби",
        "starling.ui.created_a_raid_in_your_local_village": "В вашей деревне начался рейд",
        "starling.ui.stopped_raid": "Рейд остановлен",
        "starling.ui.found_a_started_raid": "Обнаружен начавшийся рейд!",
        "starling.ui.spawned_a_raid_captain": "Появился капитан рейда",
        "starling.ui.not_currently_profiling": "Профилирование сейчас не выполняется",
        "starling.controls.joystick_mode": "Режим джойстика",
        "starling.controls.joystick_static": "Статичный джойстик",
        "starling.controls.joystick_floating": "Плавающий джойстик",
        "starling.controls.joystick_mid_bottom_left": "Слева внизу",
        "starling.controls.joystick_right_side": "Правая сторона",
        "starling.update.ask.title": "Доступна NOVA HORIZON {version}",
        "starling.update.ask.body": "Обновить сейчас? NOVA HORIZON загрузит файл ({size} МБ), затем Android установит его поверх текущей версии. Миры и настройки сохранятся.",
        "starling.update.download.title": "Загрузка NOVA HORIZON {version}",
        "starling.update.download.body": "{done} из {total} МБ",
        "starling.update.install.title": "Установить NOVA HORIZON {version}",
        "starling.update.install.body": "Android запросит установку обновления. При первом обновлении разрешите установку приложений из NOVA HORIZON. После завершения снова откройте лаунчер.",
        "starling.update.failed.title": "Не удалось загрузить обновление",
        "starling.update.button.update": "Обновить",
        "starling.update.button.tomorrow": "Завтра",
        "starling.update.button.no": "Нет",
        "starling.update.button.cancel": "Отмена",
        "starling.update.button.install": "Установить",
        "starling.update.button.later": "Позже",
        "starling.update.button.retry": "Повторить",
    })
    ru_path.write_text(json.dumps(merged_ru, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Android system notifications, file handling and diagnostics have native Russian resources too.
    values_ru = android / "res/values-ru"
    values_ru.mkdir(parents=True, exist_ok=True)
    (values_ru / "strings_ui.xml").write_text('''<resources>
    <string name="work_title">NOVA HORIZON</string>
    <string name="work_channel">NOVA HORIZON: фоновые задачи</string>
    <string name="work_default">NOVA HORIZON выполняет задачу</string>
    <string name="folder_cannot_make">Не удалось создать %1$s в %2$s</string>
    <string name="folder_no_free_name">Нет свободного имени для %1$s в %2$s</string>
    <string name="folder_cannot_rename">Не удалось переименовать %1$s в %2$s</string>
    <string name="folder_cannot_delete">Не удалось удалить %1$s</string>
    <string name="open_with">Открыть с помощью</string>
    <string name="horizon_nothing">В папке Horizon Android нет миров или наборов ресурсов</string>
    <string name="list_and"> и </string>
    <string name="mod_wants_one">%1$s запрашивает разрешение: %2$s.</string>
    <string name="mod_wants_many">%1$s запрашивают разрешения: %2$s.</string>
</resources>
''', encoding="utf-8")
    (values_ru / "folders.xml").write_text('''<resources>
    <string name="open_folder_failed">Не удалось открыть папку. Откройте приложение «Файлы» и выберите NOVA HORIZON.</string>
    <string name="opening_world">Открываем мир…</string>
</resources>
''', encoding="utf-8")
    (values_ru / "diagnostics.xml").write_text('''<resources>
    <string name="diagnostics_title">Диагностика</string>
    <string name="diagnostics_intro">Просмотр журналов и экспорт отчёта, даже если игра не запускается.</string>
    <string name="diagnostics_recovery_intro">В прошлый раз NOVA HORIZON не завершила запуск. Попробуйте снова или экспортируйте отчёт.</string>
    <string name="diagnostics_view_log">Открыть последний журнал</string>
    <string name="diagnostics_export">Экспортировать ZIP-отчёт</string>
    <string name="diagnostics_share">Поделиться последним отчётом</string>
    <string name="diagnostics_start">Попробовать запустить игру</string>
    <string name="diagnostics_working">Подготовка отчёта…</string>
    <string name="diagnostics_exported">Отчёт сохранён. Проверьте его перед отправкой.</string>
    <string name="diagnostics_failed">Не удалось выполнить диагностику: %1$s</string>
    <string name="diagnostics_no_report">Сначала экспортируйте отчёт.</string>
    <string name="diagnostics_close">Закрыть</string>
</resources>
''', encoding="utf-8")

    print("Integrated NOVA HORIZON home screen, import actions, Russian defaults and static joystick.")

if __name__ == "__main__":
    main()
