package dev.nova.horizon;

import android.app.Activity;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.InputStream;

/** Native Android home screen for NOVA HORIZON. The game itself remains the Rust NativeActivity. */
final class LauncherHome {
    interface Actions {
        void play();
        void diagnostics();
        void pick(String kind);
        void settings();
        void info();
    }

    private static final int BG = 0xE6090D1A;
    private static final int PANEL = 0xD9121728;
    private static final int PANEL_LIGHT = 0xB91B2236;
    private static final int ORANGE = 0xFFFF9D26;
    private static final int WHITE = 0xFFF3F4FA;
    private static final int MUTED = 0xFFB0B5C5;

    static View create(Activity activity, Actions actions) {
        FrameLayout root = new FrameLayout(activity);
        root.setBackgroundColor(BG);

        ImageView background = new ImageView(activity);
        background.setScaleType(ImageView.ScaleType.CENTER_CROP);
        try (InputStream input = activity.getAssets().open("launcher-bg.webp")) {
            background.setImageDrawable(new BitmapDrawable(activity.getResources(), BitmapFactory.decodeStream(input)));
        } catch (Exception ignored) {
            background.setBackground(new GradientDrawable(
                    GradientDrawable.Orientation.TL_BR,
                    new int[] {0xFF101A36, 0xFF17112C, 0xFF080B16}));
        }
        root.addView(background, new FrameLayout.LayoutParams(-1, -1));

        View shade = new View(activity);
        shade.setBackgroundColor(0xB9080B17);
        root.addView(shade, new FrameLayout.LayoutParams(-1, -1));

        ScrollView scroll = new ScrollView(activity);
        scroll.setFillViewport(true);
        scroll.setClipToPadding(false);
        scroll.setVerticalScrollBarEnabled(false);
        root.addView(scroll, new FrameLayout.LayoutParams(-1, -1));

        LinearLayout page = new LinearLayout(activity);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(activity, 18), dp(activity, 14), dp(activity, 18), dp(activity, 14));
        scroll.addView(page, new ScrollView.LayoutParams(-1, -2));

        page.addView(header(activity, actions), new LinearLayout.LayoutParams(-1, dp(activity, 58)));
        addGap(activity, page, 18);

        LinearLayout hero = new LinearLayout(activity);
        hero.setOrientation(LinearLayout.HORIZONTAL);
        hero.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout copy = new LinearLayout(activity);
        copy.setOrientation(LinearLayout.VERTICAL);
        copy.setGravity(Gravity.CENTER_VERTICAL);
        TextView eyebrow = text(activity, "MINECRAFT JAVA EDITION  •  ANDROID ARM64", 10, ORANGE, true);
        TextView title = text(activity, "NOVA HORIZON", 31, WHITE, true);
        title.setLetterSpacing(0.045f);
        TextView subtitle = text(activity, "Minecraft 26.3 — нативный Rust-клиент", 15, WHITE, false);
        TextView tagline = text(activity, "Твой мир. Твоя игра. Без Java-клиента.", 12, MUTED, false);
        copy.addView(eyebrow);
        addGap(activity, copy, 8);
        copy.addView(title);
        addGap(activity, copy, 7);
        copy.addView(subtitle);
        addGap(activity, copy, 5);
        copy.addView(tagline);
        hero.addView(copy, new LinearLayout.LayoutParams(0, -2, 1f));

        LinearLayout launch = panel(activity, 16);
        launch.setOrientation(LinearLayout.VERTICAL);
        TextView selectedLabel = text(activity, "ВЫБРАННАЯ ВЕРСИЯ", 10, MUTED, true);
        TextView version = text(activity, "◆   Minecraft 26.3", 17, WHITE, true);
        TextView engine = text(activity, "Horizon Rust  •  ARM64", 11, MUTED, false);
        TextView play = actionButton(activity, "▶   ИГРАТЬ", ORANGE, 0xFF15121B);
        play.setOnClickListener(v -> actions.play());
        TextView launchSettings = text(activity, "Настройки запуска  ⚙", 12, WHITE, true);
        launchSettings.setGravity(Gravity.CENTER);
        launchSettings.setPadding(0, dp(activity, 13), 0, dp(activity, 2));
        launchSettings.setOnClickListener(v -> actions.settings());
        launch.addView(selectedLabel);
        addGap(activity, launch, 8);
        launch.addView(version);
        addGap(activity, launch, 4);
        launch.addView(engine);
        addGap(activity, launch, 14);
        launch.addView(play, new LinearLayout.LayoutParams(-1, dp(activity, 48)));
        launch.addView(launchSettings);
        LinearLayout.LayoutParams launchParams = new LinearLayout.LayoutParams(dp(activity, 250), -2);
        launchParams.leftMargin = dp(activity, 18);
        hero.addView(launch, launchParams);
        page.addView(hero, new LinearLayout.LayoutParams(-1, -2));

        addGap(activity, page, 22);
        TextView section = text(activity, "БЫСТРЫЙ ДОСТУП", 10, MUTED, true);
        page.addView(section);
        addGap(activity, page, 10);

        HorizontalScrollView cardsScroll = new HorizontalScrollView(activity);
        cardsScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout cards = new LinearLayout(activity);
        cards.setOrientation(LinearLayout.HORIZONTAL);
        cards.addView(featureCard(activity, "⚡", "Оптимизация",
                "Диагностика FPS, CPU, GPU и памяти", actions::diagnostics));
        cards.addView(featureCard(activity, "✦", "Моды",
                "Импорт поддерживаемых модов Horizon", () -> actions.pick("mods")));
        cards.addView(featureCard(activity, "▧", "Ресурспаки",
                "Добавить текстуры и наборы ресурсов", () -> actions.pick("resources")));
        cards.addView(featureCard(activity, "☼", "Шейдеры",
                "Импорт поддерживаемых shader packs", () -> actions.pick("shaders")));
        cardsScroll.addView(cards);
        page.addView(cardsScroll, new LinearLayout.LayoutParams(-1, -2));

        addGap(activity, page, 18);
        LinearLayout footer = new LinearLayout(activity);
        footer.setGravity(Gravity.CENTER_VERTICAL);
        footer.setOrientation(LinearLayout.HORIZONTAL);
        TextView logs = smallButton(activity, "▤  ЖУРНАЛ");
        logs.setOnClickListener(v -> actions.diagnostics());
        TextView share = smallButton(activity, "↗  ОТЧЁТЫ");
        share.setOnClickListener(v -> actions.diagnostics());
        footer.addView(logs);
        LinearLayout.LayoutParams shareParams = new LinearLayout.LayoutParams(-2, dp(activity, 38));
        shareParams.leftMargin = dp(activity, 8);
        footer.addView(share, shareParams);
        TextView status = text(activity, "●  Готово к запуску  ·  ресурсы подготовятся при первом старте",
                10, MUTED, false);
        status.setGravity(Gravity.RIGHT | Gravity.CENTER_VERTICAL);
        footer.addView(status, new LinearLayout.LayoutParams(0, -1, 1f));
        page.addView(footer, new LinearLayout.LayoutParams(-1, dp(activity, 42)));

        TextView disclaimer = text(activity,
                "Требуется собственная копия Minecraft: Java Edition 26.3. Игровые файлы не входят в APK.",
                9, 0xFF8E94A6, false);
        disclaimer.setGravity(Gravity.CENTER);
        page.addView(disclaimer, new LinearLayout.LayoutParams(-1, dp(activity, 26)));
        return root;
    }

    private static View header(Activity a, Actions actions) {
        LinearLayout row = new LinearLayout(a);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout brand = panel(a, 8);
        brand.setOrientation(LinearLayout.HORIZONTAL);
        brand.setGravity(Gravity.CENTER_VERTICAL);
        TextView cube = text(a, "▣", 25, ORANGE, true);
        TextView name = text(a, "NOVA HORIZON", 15, WHITE, true);
        TextView v3 = text(a, "v3", 10, ORANGE, true);
        brand.addView(cube);
        TextView gap = text(a, " ", 1, WHITE, false);
        brand.addView(gap);
        brand.addView(name);
        TextView vgap = text(a, " ", 5, WHITE, false);
        brand.addView(vgap);
        brand.addView(v3);
        row.addView(brand, new LinearLayout.LayoutParams(-2, -1));

        HorizontalScrollView tabsScroll = new HorizontalScrollView(a);
        tabsScroll.setHorizontalScrollBarEnabled(false);
        LinearLayout tabs = new LinearLayout(a);
        tabs.setGravity(Gravity.CENTER_VERTICAL);
        tabs.setOrientation(LinearLayout.HORIZONTAL);
        String[] labels = {"Экземпляры", "Все", "Недавние", "Vanilla", "Модифицированные"};
        for (int i = 0; i < labels.length; i++) {
            TextView tab = text(a, labels[i], 11, i == 0 ? ORANGE : MUTED, i == 0);
            tab.setPadding(dp(a, 11), dp(a, 11), dp(a, 11), dp(a, 11));
            tabs.addView(tab);
        }
        tabsScroll.addView(tabs);
        row.addView(tabsScroll, new LinearLayout.LayoutParams(0, -1, 1f));

        TextView settings = smallButton(a, "⚙");
        settings.setOnClickListener(v -> actions.settings());
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(dp(a, 42), dp(a, 42));
        p.leftMargin = dp(a, 8);
        row.addView(settings, p);
        return row;
    }

    private static LinearLayout featureCard(Activity a, String icon, String title,
                                            String subtitle, Runnable click) {
        LinearLayout card = panel(a, 13);
        card.setOrientation(LinearLayout.VERTICAL);
        TextView glyph = text(a, icon, 22, ORANGE, true);
        TextView heading = text(a, title, 15, WHITE, true);
        TextView description = text(a, subtitle, 10, MUTED, false);
        description.setMaxLines(2);
        card.addView(glyph);
        addGap(a, card, 10);
        card.addView(heading);
        addGap(a, card, 5);
        card.addView(description);
        card.setOnClickListener(v -> click.run());
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(dp(a, 176), dp(a, 112));
        p.rightMargin = dp(a, 10);
        card.setLayoutParams(p);
        return card;
    }

    private static LinearLayout panel(Activity a, int padding) {
        LinearLayout box = new LinearLayout(a);
        box.setPadding(dp(a, padding), dp(a, padding), dp(a, padding), dp(a, padding));
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(PANEL);
        shape.setCornerRadius(dp(a, 16));
        shape.setStroke(dp(a, 1), 0x42FFFFFF);
        box.setBackground(shape);
        box.setElevation(dp(a, 3));
        return box;
    }

    private static TextView actionButton(Activity a, String value, int background, int foreground) {
        TextView view = text(a, value, 15, foreground, true);
        view.setGravity(Gravity.CENTER);
        view.setPadding(dp(a, 12), 0, dp(a, 12), 0);
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(background);
        shape.setCornerRadius(dp(a, 13));
        view.setBackground(shape);
        view.setClickable(true);
        view.setFocusable(true);
        return view;
    }

    private static TextView smallButton(Activity a, String value) {
        TextView view = text(a, value, 10, WHITE, true);
        view.setGravity(Gravity.CENTER);
        view.setPadding(dp(a, 12), 0, dp(a, 12), 0);
        GradientDrawable shape = new GradientDrawable();
        shape.setColor(PANEL_LIGHT);
        shape.setCornerRadius(dp(a, 11));
        shape.setStroke(dp(a, 1), 0x38FFFFFF);
        view.setBackground(shape);
        view.setClickable(true);
        view.setFocusable(true);
        return view;
    }

    private static TextView text(Activity a, String value, float size, int color, boolean bold) {
        TextView view = new TextView(a);
        view.setText(value);
        view.setTextSize(size);
        view.setTextColor(color);
        view.setTypeface(Typeface.create("sans-serif", bold ? Typeface.BOLD : Typeface.NORMAL));
        view.setIncludeFontPadding(false);
        return view;
    }

    private static void addGap(Activity a, LinearLayout parent, int dp) {
        View gap = new View(a);
        parent.addView(gap, new LinearLayout.LayoutParams(1, LauncherHome.dp(a, dp)));
    }

    private static int dp(Activity a, int value) {
        return Math.round(value * a.getResources().getDisplayMetrics().density);
    }
}
