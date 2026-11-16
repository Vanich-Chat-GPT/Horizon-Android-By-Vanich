package dev.nova.horizon

object NativeBridge {
    private val loadFailure: String? = runCatching {
        System.loadLibrary("nova_core")
    }.exceptionOrNull()?.message

    external fun nativeCoreStatus(): String

    fun status(): String {
        val failure = loadFailure
        if (failure != null) return "Rust Core недоступен: $failure"
        return runCatching { nativeCoreStatus() }
            .getOrElse { "Ошибка JNI: ${it.message ?: "неизвестная ошибка"}" }
    }
}
