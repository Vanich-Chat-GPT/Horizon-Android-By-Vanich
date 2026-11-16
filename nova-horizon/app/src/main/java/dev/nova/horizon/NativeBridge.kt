package dev.nova.horizon

object NativeBridge {
    private val loadFailure: String? = runCatching {
        System.loadLibrary("nova_core")
    }.exceptionOrNull()?.message

    external fun nativeCoreStatus(): String
    private external fun nativeInspectVersionManifest(json: String): String

    fun status(): String {
        val failure = loadFailure
        if (failure != null) return "Rust Core недоступен: " + failure
        return runCatching { nativeCoreStatus() }
            .getOrElse { "Ошибка JNI: " + (it.message ?: "неизвестная ошибка") }
    }

    fun inspectVersionManifest(json: String): String {
        val failure = loadFailure
        if (failure != null) {
            throw IllegalStateException("Rust Core недоступен: " + failure)
        }
        return nativeInspectVersionManifest(json)
    }
}
