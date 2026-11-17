package dev.nova.horizon

import android.content.Context

internal enum class JoystickMode(val storageValue: String, val label: String) {
    STATIC("static", "Статичный"),
    FLOATING("floating", "Плавающий");

    companion object {
        fun fromStorage(value: String?): JoystickMode =
            entries.firstOrNull { it.storageValue == value } ?: STATIC
    }
}

internal data class TouchControlSettings(
    val enabled: Boolean = true,
    val joystickMode: JoystickMode = JoystickMode.STATIC,
    val controlScale: Float = 1.0f,
    val opacity: Float = 0.82f,
    val sensitivity: Float = 1.0f,
    val leftHanded: Boolean = false,
    val showDpad: Boolean = false
)

internal object TouchControlSettingsStore {
    private const val PREFS = "nova_touch_controls_v1"

    fun read(context: Context): TouchControlSettings {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return TouchControlSettings(
            enabled = prefs.getBoolean("enabled", true),
            joystickMode = JoystickMode.fromStorage(prefs.getString("joystick_mode", "static")),
            controlScale = prefs.getFloat("control_scale", 1.0f).coerceIn(0.6f, 1.4f),
            opacity = prefs.getFloat("opacity", 0.82f).coerceIn(0.3f, 1.0f),
            sensitivity = prefs.getFloat("sensitivity", 1.0f).coerceIn(0.5f, 2.0f),
            leftHanded = prefs.getBoolean("left_handed", false),
            showDpad = prefs.getBoolean("show_dpad", false)
        )
    }

    fun save(context: Context, settings: TouchControlSettings) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putBoolean("enabled", settings.enabled)
            .putString("joystick_mode", settings.joystickMode.storageValue)
            .putFloat("control_scale", settings.controlScale.coerceIn(0.6f, 1.4f))
            .putFloat("opacity", settings.opacity.coerceIn(0.3f, 1.0f))
            .putFloat("sensitivity", settings.sensitivity.coerceIn(0.5f, 2.0f))
            .putBoolean("left_handed", settings.leftHanded)
            .putBoolean("show_dpad", settings.showDpad)
            .apply()
    }
}
