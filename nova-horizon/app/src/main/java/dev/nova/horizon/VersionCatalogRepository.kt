package dev.nova.horizon

import java.io.ByteArrayOutputStream
import java.net.URI
import java.net.URL
import java.nio.charset.StandardCharsets
import javax.net.ssl.HttpsURLConnection

internal data class OfficialVersionCatalog(
    val latestRelease: String,
    val latestSnapshot: String,
    val versionCount: Int
)

/**
 * Reads Mojang's public version index only. This class does not install game files,
 * grant an account entitlement, or claim that a version can run on this device.
 */
internal object VersionCatalogRepository {
    private const val MANIFEST_URL =
        "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    private const val OFFICIAL_HOST = "piston-meta.mojang.com"
    private const val MAX_RESPONSE_BYTES = 8 * 1024 * 1024

    fun fetch(): OfficialVersionCatalog {
        val body = downloadOfficialManifest()
        val nativeResult = NativeBridge.inspectVersionManifest(body)
        val fields = nativeResult.split('|')

        if (fields.firstOrNull() != "OK" || fields.size != 4) {
            val detail = fields.drop(1).joinToString(" ").ifBlank { "Неизвестная ошибка проверки" }
            throw IllegalStateException("Проверка Rust Core отклонена: " + detail)
        }

        val release = fields[1]
        val snapshot = fields[2]
        val count = fields[3].toIntOrNull()
            ?: throw IllegalStateException("Rust Core вернул некорректное количество версий")

        if (release.isBlank() || snapshot.isBlank() || count <= 0) {
            throw IllegalStateException("Официальный каталог не прошёл проверку")
        }

        return OfficialVersionCatalog(release, snapshot, count)
    }

    private fun downloadOfficialManifest(): String {
        var currentUrl = URL(MANIFEST_URL)
        repeat(4) { redirectCount ->
            validateOfficialUrl(currentUrl)
            val connection = (currentUrl.openConnection() as HttpsURLConnection).apply {
                connectTimeout = 12_000
                readTimeout = 20_000
                requestMethod = "GET"
                instanceFollowRedirects = false
                setRequestProperty("Accept", "application/json")
                setRequestProperty("User-Agent", "NOVA-HORIZON/0.1.0-dev (Android)")
            }

            try {
                val status = connection.responseCode
                if (status in 300..399) {
                    if (redirectCount == 3) {
                        throw IllegalStateException("Слишком много перенаправлений официального каталога")
                    }
                    val location = connection.getHeaderField("Location")
                        ?: throw IllegalStateException("Сервер вернул перенаправление без адреса")
                    currentUrl = URL(currentUrl, location)
                    validateOfficialUrl(currentUrl)
                    return@repeat
                }
                if (status !in 200..299) {
                    throw IllegalStateException(
                        "Официальный каталог вернул HTTP " + status
                    )
                }

                val contentType = connection.contentType.orEmpty()
                if (contentType.isNotBlank() &&
                    !contentType.lowercase().startsWith("application/json")
                ) {
                    throw IllegalStateException(
                        "Неожиданный тип ответа каталога: " + contentType
                    )
                }

                val bytes = connection.inputStream.use { input ->
                    val output = ByteArrayOutputStream()
                    val buffer = ByteArray(16 * 1024)
                    var total = 0
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        total += read
                        if (total > MAX_RESPONSE_BYTES) {
                            throw IllegalStateException("Ответ каталога превышает допустимый размер")
                        }
                        output.write(buffer, 0, read)
                    }
                    output.toByteArray()
                }
                return String(bytes, StandardCharsets.UTF_8)
            } finally {
                connection.disconnect()
            }
        }
        throw IllegalStateException("Не удалось получить официальный каталог версий")
    }

    private fun validateOfficialUrl(url: URL) {
        val uri = URI(url.toString())
        if (!uri.scheme.equals("https", ignoreCase = true) ||
            !uri.host.equals(OFFICIAL_HOST, ignoreCase = true) ||
            uri.userInfo != null ||
            (uri.port != -1 && uri.port != 443)
        ) {
            throw SecurityException("Заблокирован недоверенный адрес метаданных Minecraft")
        }
    }
}
