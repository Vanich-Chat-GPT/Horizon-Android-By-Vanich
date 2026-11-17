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

    add_translations(
        root / "crates/horizon-client/assets/horizon/lang/en_us.json",
        {
            "starling.ui.touch_controls": "Touch Controls",
            "starling.controls.joystick_mode": "Joystick mode",
            "starling.controls.joystick_static": "Static joystick",
            "starling.controls.joystick_floating": "Floating joystick",
            "starling.controls.joystick_mid_bottom_left": "Mid-bottom left",
            "starling.controls.joystick_right_side": "Right side",
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
    })
    ru_path.write_text(json.dumps(merged_ru, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")

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
