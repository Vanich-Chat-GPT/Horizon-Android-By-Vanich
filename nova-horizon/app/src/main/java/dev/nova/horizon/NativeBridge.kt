package dev.nova.horizon

object NativeBridge {
    private val loadFailure: String? = runCatching {
        System.loadLibrary("nova_core")
    }.exceptionOrNull()?.message

    external fun nativeCoreStatus(): String
    private external fun nativeParseVersionCatalog(json: String): String
    private external fun nativeInspectVersionMetadata(json: String, expectedId: String): String
    private external fun nativeBuildInstallPlan(json: String, expectedId: String): String

    fun status(): String {
        val failure = loadFailure
        if (failure != null) return "Rust Core недоступен: " + failure
        return runCatching { nativeCoreStatus() }
            .getOrElse { "Ошибка JNI: " + (it.message ?: "неизвестная ошибка") }
    }

    fun parseVersionCatalog(json: String): String {
        ensureLoaded()
        return nativeParseVersionCatalog(json)
    }

    fun inspectVersionMetadata(json: String, expectedId: String): String {
        ensureLoaded()
        return nativeInspectVersionMetadata(json, expectedId)
    }

    fun buildInstallPlan(json: String, expectedId: String): String {
        ensureLoaded()
        return nativeBuildInstallPlan(json, expectedId)
    }

    private fun ensureLoaded() {
        val failure = loadFailure
        if (failure != null) {
            throw IllegalStateException("Rust Core недоступен: " + failure)
        }
    }
}
