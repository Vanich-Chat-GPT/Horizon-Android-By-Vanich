package dev.nova.horizon;

import android.app.Activity;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/**
 * Native Android port of Horizon Launcher's original Night home screen.
 * Layout follows the upstream desktop launcher: top navigation, instance/server sidebar,
 * pixel-art landscape hero, edition tabs, Play/version/folder actions and glass tabbed panel.
 */
final class LauncherHome {
    interface Actions {
        void play();
        void diagnostics();
        void pick(String kind);
        void settings();
        void info();
    }

    private static final int PAGE = 0xFF0D0E13;
    private static final int PLATE = 0xFF16181F;
    private static final int PLATE_SOFT = 0xFF181A22;
    private static final int RULE = 0xFF24262F;
    private static final int INK = 0xFFECEDF3;
    private static final int SOFT = 0xFFC5C7D1;
    private static final int MUTED = 0xFF8B8F9C;
    private static final int ACCENT = 0xFF9A86FF;
    private static final int SUCCESS = 0xFF45C27A;

    static View create(Activity a, Actions actions) {
        LinearLayout root = new LinearLayout(a);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(PAGE);

        root.addView(topBar(a, actions), new LinearLayout.LayoutParams(-1, dp(a, 58)));

        LinearLayout body = new LinearLayout(a);
        body.setOrientation(LinearLayout.HORIZONTAL);
        body.addView(sidebar(a, actions), new LinearLayout.LayoutParams(dp(a, 222), -1));

        ScrollView scroll = new ScrollView(a);
        scroll.setFillViewport(true);
        scroll.setVerticalScrollBarEnabled(false);
        LinearLayout content = new LinearLayout(a);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(a, 32), dp(a, 20), dp(a, 30), dp(a, 28));
        scroll.addView(content, new ScrollView.LayoutParams(-1, -2));
        content.addView(hero(a, actions), new LinearLayout.LayoutParams(-1, dp(a, 320)));
        gap(a, content, 18);
        content.addView(homeTabs(a, actions), new LinearLayout.LayoutParams(-1, -2));
        body.addView(scroll, new LinearLayout.LayoutParams(0, -1, 1f));
        root.addView(body, new LinearLayout.LayoutParams(-1, 0, 1f));
        return root;
    }

    private static View topBar(Activity a, Actions actions) {
        LinearLayout bar = new LinearLayout(a);
        bar.setGravity(Gravity.CENTER_VERTICAL);
        bar.setPadding(dp(a, 22), 0, dp(a, 20), 0);
        bar.setBackgroundColor(PAGE);
        TextView mark = label(a, "▰", 22, ACCENT, true);
        bar.addView(mark);
        TextView brand = label(a, "Horizon", 19, INK, true);
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-2, -2);
        bp.leftMargin = dp(a, 10);
        bar.addView(brand, bp);
        TextView edition = label(a, "RUST EDITION", 9, MUTED, true);
        LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(-2, -2);
        ep.leftMargin = dp(a, 12);
        bar.addView(edition, ep);

        View spacer = new View(a);
        bar.addView(spacer, new LinearLayout.LayoutParams(0, 1, 1f));
        String[] nav = {"Главная", "Моды", "Версии", "Заметки", "Серверы"};
        for (int i = 0; i < nav.length; i++) {
            TextView item = label(a, nav[i], 12, i == 0 ? INK : MUTED, i == 0);
            item.setPadding(dp(a, 12), dp(a, 10), dp(a, 12), dp(a, 10));
            if (i == 0) item.setBackground(round(0x22FFFFFF, 10));
            final int index = i;
            item.setOnClickListener(v -> {
                if (index == 1) actions.pick("mods");
                else if (index == 2) actions.info();
                else if (index == 3 || index == 4) actions.diagnostics();
            });
            bar.addView(item);
        }
        TextView account = label(a, "  ◉  Аккаунт  ", 11, SOFT, true);
        account.setPadding(dp(a, 12), dp(a, 9), dp(a, 12), dp(a, 9));
        account.setBackground(round(PLATE_SOFT, 18));
        LinearLayout.LayoutParams ap = new LinearLayout.LayoutParams(-2, -2);
        ap.leftMargin = dp(a, 12);
        bar.addView(account, ap);
        TextView settings = label(a, "⚙", 20, SOFT, false);
        settings.setGravity(Gravity.CENTER);
        settings.setOnClickListener(v -> actions.settings());
        LinearLayout.LayoutParams sp = new LinearLayout.LayoutParams(dp(a, 42), -1);
        sp.leftMargin = dp(a, 8);
        bar.addView(settings, sp);
        View rule = new View(a);
        rule.setBackgroundColor(RULE);
        FrameLayout wrap = new FrameLayout(a);
        wrap.addView(bar, new FrameLayout.LayoutParams(-1, -1));
        wrap.addView(rule, new FrameLayout.LayoutParams(-1, dp(a, 1), Gravity.BOTTOM));
        return wrap;
    }

    private static View sidebar(Activity a, Actions actions) {
        LinearLayout side = new LinearLayout(a);
        side.setOrientation(LinearLayout.VERTICAL);
        side.setPadding(dp(a, 14), dp(a, 22), dp(a, 12), dp(a, 14));
        side.setBackgroundColor(0xFF101117);
        TextView instances = label(a, "ЭКЗЕМПЛЯРЫ", 10, MUTED, true);
        side.addView(instances);
        gap(a, side, 12);
        side.addView(sideRow(a, "▰", "Horizon", "Minecraft 26.3 · Готов", true));
        gap(a, side, 8);
        TextView add = label(a, "+  Добавить экземпляр", 12, SOFT, false);
        add.setPadding(dp(a, 10), dp(a, 12), dp(a, 4), dp(a, 12));
        add.setOnClickListener(v -> actions.info());
        side.addView(add);
        gap(a, side, 26);
        side.addView(label(a, "СЕРВЕРЫ", 10, MUTED, true));
        gap(a, side, 10);
        side.addView(sideRow(a, "⌁", "Мультиплеер", "Подключение к серверу", false));
        gap(a, side, 24);
        side.addView(label(a, "БИБЛИОТЕКА", 10, MUTED, true));
        gap(a, side, 10);
        side.addView(sideRow(a, "◇", "Моды", "Поддерживаемые моды", false));
        side.addView(sideRow(a, "▧", "Ресурспаки", "Текстуры и ресурсы", false));
        side.addView(sideRow(a, "▤", "Миры", "Локальные сохранения", false));
        View spacer = new View(a);
        side.addView(spacer, new LinearLayout.LayoutParams(1, 0, 1f));
        View rule = new View(a);
        rule.setBackgroundColor(RULE);
        side.addView(rule, new LinearLayout.LayoutParams(-1, dp(a, 1)));
        gap(a, side, 12);
        side.addView(label(a, "HORIZON · ANDROID", 9, MUTED, true));
        side.addView(label(a, "NOVA HORIZON v3.0.0", 10, SOFT, false));
        return side;
    }

    private static View sideRow(Activity a, String icon, String title, String note, boolean selected) {
        LinearLayout row = new LinearLayout(a);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setPadding(dp(a, 9), dp(a, 9), dp(a, 6), dp(a, 9));
        row.setBackground(round(selected ? 0x1FFFFFFF : 0x00000000, 11));
        TextView glyph = label(a, icon, 19, selected ? ACCENT : MUTED, true);
        row.addView(glyph);
        LinearLayout text = new LinearLayout(a);
        text.setOrientation(LinearLayout.VERTICAL);
        TextView name = label(a, title, 12, selected ? INK : SOFT, true);
        TextView detail = label(a, note, 9, MUTED, false);
        text.addView(name);
        gap(a, text, 3);
        text.addView(detail);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, -2, 1f);
        p.leftMargin = dp(a, 10);
        row.addView(text, p);
        return row;
    }

    private static View hero(Activity a, Actions actions) {
        FrameLayout frame = new FrameLayout(a);
        frame.setBackground(round(PLATE, 14));
        frame.setClipToOutline(true);
        PixelLandscape landscape = new PixelLandscape(a);
        frame.addView(landscape, new FrameLayout.LayoutParams(-1, -1));
        View veil = new View(a);
        veil.setBackground(new android.graphics.drawable.GradientDrawable(
                android.graphics.drawable.GradientDrawable.Orientation.TOP_BOTTOM,
                new int[]{0x40100D20, 0xB80D0E13}));
        frame.addView(veil, new FrameLayout.LayoutParams(-1, -1));

        LinearLayout copy = new LinearLayout(a);
        copy.setOrientation(LinearLayout.VERTICAL);
        copy.setPadding(dp(a, 28), dp(a, 24), dp(a, 24), dp(a, 20));
        TextView edition = label(a, "▰  RUST EDITION     ·     JAVA EDITION 26.3", 10, SOFT, true);
        copy.addView(edition);
        gap(a, copy, 24);
        TextView state = label(a, "●  ГОТОВ К ЗАПУСКУ  ·  ARM64", 10, SUCCESS, true);
        copy.addView(state);
        gap(a, copy, 8);
        TextView title = label(a, "Horizon", 54, INK, true);
        title.setLetterSpacing(-0.035f);
        copy.addView(title);
        gap(a, copy, 5);
        copy.addView(label(a, "Minecraft: Java Edition 26.3, переписанный на Rust", 14, SOFT, false));
        gap(a, copy, 5);
        copy.addView(label(a, "Вы ещё не запускали этот экземпляр. Нажмите «Играть».", 11, SOFT, false));

        LinearLayout actionsRow = new LinearLayout(a);
        actionsRow.setGravity(Gravity.CENTER_VERTICAL);
        actionsRow.setOrientation(LinearLayout.HORIZONTAL);
        actionsRow.setPadding(0, dp(a, 24), 0, 0);
        TextView play = pill(a, "▶   ИГРАТЬ", ACCENT, 0xFF0D0E13, true);
        play.setOnClickListener(v -> actions.play());
        actionsRow.addView(play, new LinearLayout.LayoutParams(dp(a, 176), dp(a, 48)));
        TextView version = pill(a, "Версия  ·  26.3   ⌄", 0xD91D1A2B, INK, false);
        LinearLayout.LayoutParams vp = new LinearLayout.LayoutParams(dp(a, 176), dp(a, 48));
        vp.leftMargin = dp(a, 10);
        actionsRow.addView(version, vp);
        version.setOnClickListener(v -> actions.info());
        TextView mods = pill(a, "⌘", 0xD91D1A2B, INK, false);
        LinearLayout.LayoutParams mp = new LinearLayout.LayoutParams(dp(a, 48), dp(a, 48));
        mp.leftMargin = dp(a, 10);
        actionsRow.addView(mods, mp);
        mods.setOnClickListener(v -> actions.pick("mods"));
        TextView folder = pill(a, "▱", 0xD91D1A2B, INK, false);
        LinearLayout.LayoutParams fp = new LinearLayout.LayoutParams(dp(a, 48), dp(a, 48));
        fp.leftMargin = dp(a, 8);
        actionsRow.addView(folder, fp);
        folder.setOnClickListener(v -> actions.pick("all"));
        copy.addView(actionsRow);
        frame.addView(copy, new FrameLayout.LayoutParams(-1, -1));

        LinearLayout invite = new LinearLayout(a);
        invite.setOrientation(LinearLayout.VERTICAL);
        invite.setPadding(dp(a, 14), dp(a, 12), dp(a, 14), dp(a, 12));
        invite.setBackground(round(0xAA171521, 12));
        invite.addView(label(a, "ИГРАТЬ С ДРУЗЬЯМИ", 9, MUTED, true));
        gap(a, invite, 8);
        invite.addView(label(a, "Пригласить друга", 15, INK, true));
        gap(a, invite, 4);
        invite.addView(label(a, "Скопируйте код мира после запуска игры", 10, SOFT, false));
        FrameLayout.LayoutParams ip = new FrameLayout.LayoutParams(dp(a, 210), -2, Gravity.RIGHT | Gravity.BOTTOM);
        ip.setMargins(0, 0, dp(a, 18), dp(a, 18));
        frame.addView(invite, ip);
        return frame;
    }

    private static View homeTabs(Activity a, Actions actions) {
        LinearLayout outer = new LinearLayout(a);
        outer.setOrientation(LinearLayout.VERTICAL);
        outer.setBackground(round(PLATE, 14));
        LinearLayout tabs = new LinearLayout(a);
        tabs.setGravity(Gravity.CENTER_VERTICAL);
        tabs.setPadding(dp(a, 10), dp(a, 8), dp(a, 10), dp(a, 8));
        String[] names = {"Обзор", "Моды", "Миры", "Сетевая игра", "Наборы", "Скриншоты", "Консоль"};
        for (int i = 0; i < names.length; i++) {
            final int index = i;
            TextView tab = label(a, names[i], 11, i == 0 ? INK : MUTED, i == 0);
            tab.setPadding(dp(a, 12), dp(a, 9), dp(a, 12), dp(a, 9));
            if (i == 0) tab.setBackground(round(0x24FFFFFF, 9));
            tab.setOnClickListener(v -> {
                if (index == 1) actions.pick("mods");
                else if (index == 2) actions.info();
                else if (index == 3) actions.info();
                else if (index == 4) actions.pick("resources");
                else if (index == 5 || index == 6) actions.diagnostics();
            });
            tabs.addView(tab);
        }
        outer.addView(tabs);
        View rule = new View(a);
        rule.setBackgroundColor(RULE);
        outer.addView(rule, new LinearLayout.LayoutParams(-1, dp(a, 1)));

        LinearLayout panel = new LinearLayout(a);
        panel.setPadding(dp(a, 18), dp(a, 16), dp(a, 18), dp(a, 18));
        panel.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout shots = new LinearLayout(a);
        shots.setOrientation(LinearLayout.VERTICAL);
        shots.addView(label(a, "СКРИНШОТЫ", 10, MUTED, true));
        gap(a, shots, 12);
        shots.addView(label(a, "Здесь появятся ваши последние игровые снимки.", 13, SOFT, false));
        shots.addView(label(a, "Нажмите F2 в игре, чтобы сделать скриншот.", 10, MUTED, false));
        panel.addView(shots, new LinearLayout.LayoutParams(0, dp(a, 104), 1f));
        View divider = new View(a);
        divider.setBackgroundColor(RULE);
        LinearLayout.LayoutParams dpv = new LinearLayout.LayoutParams(dp(a, 1), -1);
        dpv.leftMargin = dp(a, 14);
        dpv.rightMargin = dp(a, 14);
        panel.addView(divider, dpv);
        LinearLayout notes = new LinearLayout(a);
        notes.setOrientation(LinearLayout.VERTICAL);
        notes.addView(label(a, "ПОСЛЕДНИЕ ИЗМЕНЕНИЯ", 10, MUTED, true));
        gap(a, notes, 12);
        notes.addView(label(a, "NOVA HORIZON · Android ARM64", 14, INK, true));
        gap(a, notes, 5);
        notes.addView(label(a, "Horizon Rust · Minecraft Java Edition 26.3", 11, SOFT, false));
        panel.addView(notes, new LinearLayout.LayoutParams(0, -2, 1f));
        outer.addView(panel);
        return outer;
    }

    private static TextView pill(Activity a, String text, int bg, int fg, boolean bold) {
        TextView v = label(a, text, 12, fg, bold);
        v.setGravity(Gravity.CENTER);
        v.setBackground(round(bg, 11));
        return v;
    }

    private static TextView label(Activity a, String value, float size, int color, boolean bold) {
        TextView v = new TextView(a);
        v.setText(value);
        v.setTextSize(size);
        v.setTextColor(color);
        v.setIncludeFontPadding(false);
        v.setTypeface(Typeface.create("sans-serif", bold ? Typeface.BOLD : Typeface.NORMAL));
        return v;
    }

    private static GradientDrawable round(int color, int radius) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(radius);
        return d;
    }

    private static void gap(Activity a, LinearLayout parent, int height) {
        parent.addView(new View(a), new LinearLayout.LayoutParams(1, dp(a, height)));
    }

    private static int dp(Activity a, int value) {
        return Math.round(value * a.getResources().getDisplayMetrics().density);
    }

    /** Low-cost procedural version of Horizon's original pixel-art Night landscape. */
    private static final class PixelLandscape extends View {
        private final Paint p = new Paint();
        PixelLandscape(Activity a) { super(a); setLayerType(View.LAYER_TYPE_HARDWARE, null); }
        private void rect(Canvas c, int color, float x, float y, float w, float h) {
            p.setColor(color);
            p.setStyle(Paint.Style.FILL);
            c.drawRect(x, y, x + w, y + h, p);
        }
        @Override protected void onDraw(Canvas c) {
            super.onDraw(c);
            float w = getWidth(), h = getHeight();
            rect(c, 0xFF241B43, 0, 0, w, h * .25f);
            rect(c, 0xFF33204D, 0, h * .25f, w, h * .22f);
            rect(c, 0xFF4A2858, 0, h * .47f, w, h * .20f);
            rect(c, 0xFF733B68, 0, h * .67f, w, h * .15f);
            rect(c, 0xFF9A526F, 0, h * .82f, w, h * .18f);
            for (int i = 0; i < 58; i++) {
                float x = ((i * 97) % 997) / 997f * w;
                float y = ((i * 53) % 401) / 401f * h * .55f;
                rect(c, (i % 4 == 0) ? 0xFFE7D9F5 : 0xFFB7A6D5, x, y, i % 7 == 0 ? 3 : 2, 2);
            }
            float sunX = w * .74f, sunY = h * .62f, r = Math.min(w, h) * .12f;
            for (int i = 0; i < 5; i++) {
                float bandY = sunY - r + i * r * .42f;
                rect(c, i < 2 ? 0xFFFFD08B : 0xFFFFA66F, sunX - r, bandY, r * 2, r * .30f);
            }
            for (int layer = 0; layer < 2; layer++) {
                int color = layer == 0 ? 0xFF38234F : 0xFF171329;
                float base = layer == 0 ? h * .86f : h * .96f;
                float x = layer == 0 ? -20 : 0;
                int n = 0;
                while (x < w + 30) {
                    float bw = (layer == 0 ? 34 : 24) + (n * 13 % 31);
                    float bh = (layer == 0 ? 32 : 24) + (n * 17 % 38);
                    rect(c, color, x, base - bh, bw, bh);
                    if (layer == 1 && n % 3 == 0) {
                        rect(c, color, x + bw * .32f, base - bh - 18, bw * .34f, 18);
                    }
                    x += bw - (layer == 0 ? 5 : 2);
                    n++;
                }
            }
        }
    }
}
