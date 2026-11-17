package dev.nova.horizon

import java.io.ByteArrayOutputStream
import java.net.URI
import java.net.URL
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.util.Locale
import javax.net.ssl.HttpsURLConnection
import org.json.JSONArray
import org.json.JSONObject

internal data class OfficialVersion(
    val id: String,
    val type: String,
    val metadataUrl: String,
    val sha1: String,
    val releaseTime: String,
    val complianceLevel: Int?
)

internal data class OfficialVersionCatalog(
    val latestRelease: String,
    val latestSnapshot: String,
    val versions: List<OfficialVersion>
) {
    val versionCount: Int get() = versions.size
}

internal data class VersionMetadataSummary(
    val id: String,
    val type: String,
    val mainClass: String,
    val javaMajor: Int?,
    val assetIndexId: String?,
    val clientSize: Long?,
    val libraryCount: Int
)

internal data class PlannedArtifact(
    val kind: String,
    val url: String,
    val sha1: String,
    val size: Long,
    val relativePath: String
)

internal data class InstallPlanIssue(
    val library: String,
    val reason: String
)

internal data class AndroidInstallPlan(
    val versionId: String,
    val javaMajorVersion: Int?,
    val client: PlannedArtifact,
    val assetIndex: PlannedArtifact,
    val libraries: List<PlannedArtifact>,
    val issues: List<InstallPlanIssue>,
    val totalDownloadBytes: Long,
    val launchReady: Boolean
) {
    val artifactCount: Int get() = 2 + libraries.size
}

internal data class VersionInspection(
    val metadata: VersionMetadataSummary,
    val plan: AndroidInstallPlan
)

/**
 * Reads Mojang's public version index and selected per-version JSON metadata.
 *
 * This class does not install game files or grant an account entitlement. Per-version
 * JSON is accepted only when its bytes match the SHA-1 declared by the official index.
 */
internal object VersionCatalogRepository {
    private const val MANIFEST_URL =
        "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    private const val OFFICIAL_HOST = "piston-meta.mojang.com"
    private const val MAX_MANIFEST_BYTES = 8 * 1024 * 1024
    private const val MAX_VERSION_METADATA_BYTES = 16 * 1024 * 1024

    fun fetch(): OfficialVersionCatalog {
        val body = downloadOfficial(
            MANIFEST_URL,
            maxBytes = MAX_MANIFEST_BYTES,
            expectedSha1 = null
        )
        val normalized = JSONObject(
            NativeBridge.parseVersionCatalog(String(body, StandardCharsets.UTF_8))
        )
        if (normalized.has("ok") && !normalized.optBoolean("ok")) {
            throw IllegalStateException(
                "Rust Core отклонил официальный каталог: " + normalized.optString("error")
            )
        }

        val latest = normalized.getJSONObject("latest")
        val entries = normalized.getJSONArray("versions")
        val versions = ArrayList<OfficialVersion>(entries.length())
        for (index in 0 until entries.length()) {
            val entry = entries.getJSONObject(index)
            val id = entry.getString("id")
            val url = entry.getString("url")
            val sha1 = entry.getString("sha1")
            if (!isValidVersionId(id) || !isSha1(sha1)) {
                throw SecurityException("Rust Core вернул некорректную запись версии")
            }
            validateOfficialUrl(URL(url))
            versions += OfficialVersion(
                id = id,
                type = entry.getString("type"),
                metadataUrl = url,
                sha1 = sha1.lowercase(Locale.ROOT),
                releaseTime = entry.getString("releaseTime"),
                complianceLevel = if (entry.isNull("complianceLevel")) {
                    null
                } else {
                    entry.optInt("complianceLevel")
                }
            )
        }

        if (versions.isEmpty()) {
            throw IllegalStateException("Официальный каталог не содержит версий")
        }

        return OfficialVersionCatalog(
            latestRelease = latest.getString("release"),
            latestSnapshot = latest.getString("snapshot"),
            versions = versions
        )
    }

    /**
     * Fetches the selected descriptor, verifies the manifest SHA-1, then asks Rust Core
     * to validate its schema and construct a conservative Android ARM64 install plan.
     */
    fun inspectVersion(version: OfficialVersion): VersionInspection {
        val bytes = downloadOfficial(
            version.metadataUrl,
            maxBytes = MAX_VERSION_METADATA_BYTES,
            expectedSha1 = version.sha1
        )
        val json = String(bytes, StandardCharsets.UTF_8)
        val native = JSONObject(NativeBridge.inspectVersionMetadata(json, version.id))
        if (!native.optBoolean("ok", false)) {
            throw SecurityException(
                "Метаданные версии " + version.id + " отклонены: " +
                    native.optString("error", "неизвестная ошибка")
            )
        }

        val summary = VersionMetadataSummary(
            id = native.getString("id"),
            type = native.getString("versionType"),
            mainClass = native.getString("mainClass"),
            javaMajor = if (native.isNull("javaMajor")) null else native.optInt("javaMajor"),
            assetIndexId = if (native.isNull("assetIndexId")) null else native.optString("assetIndexId"),
            clientSize = if (native.isNull("clientSize")) null else native.optLong("clientSize"),
            libraryCount = native.optInt("libraryCount")
        )

        val planJson = JSONObject(NativeBridge.buildInstallPlan(json, version.id))
        if (!planJson.optBoolean("versionId") && !planJson.has("versionId")) {
            throw SecurityException("Rust Core не вернул план установки версии")
        }
        if (planJson.has("ok") && !planJson.optBoolean("ok")) {
            throw SecurityException("План установки отклонён: " + planJson.optString("error"))
        }

        val librariesJson = planJson.getJSONArray("libraries")
        val libraries = ArrayList<PlannedArtifact>(librariesJson.length())
        for (index in 0 until librariesJson.length()) {
            libraries += parseArtifact(librariesJson.getJSONObject(index))
        }

        val issuesJson = planJson.getJSONArray("issues")
        val issues = ArrayList<InstallPlanIssue>(issuesJson.length())
        for (index in 0 until issuesJson.length()) {
            val issue = issuesJson.getJSONObject(index)
            issues += InstallPlanIssue(
                library = issue.getString("library"),
                reason = issue.getString("reason")
            )
        }

        val plan = AndroidInstallPlan(
            versionId = planJson.getString("versionId"),
            javaMajorVersion = if (planJson.isNull("javaMajorVersion")) {
                null
            } else {
                planJson.optInt("javaMajorVersion")
            },
            client = parseArtifact(planJson.getJSONObject("client")),
            assetIndex = parseArtifact(planJson.getJSONObject("assetIndex")),
            libraries = libraries,
            issues = issues,
            totalDownloadBytes = planJson.getLong("totalDownloadBytes"),
            launchReady = planJson.getBoolean("launchReady")
        )

        if (plan.versionId != version.id || plan.launchReady) {
            throw SecurityException("Rust Core вернул неожиданный или небезопасный план")
        }

        return VersionInspection(summary, plan)
    }

    private fun parseArtifact(value: JSONObject) = PlannedArtifact(
        kind = value.getString("kind"),
        url = value.getString("url"),
        sha1 = value.getString("sha1"),
        size = value.getLong("size"),
        relativePath = value.getString("relativePath")
    )

    private fun downloadOfficial(
        address: String,
        maxBytes: Int,
        expectedSha1: String?
    ): ByteArray {
        var currentUrl = URL(address)
        for (redirectCount in 0..3) {
            validateOfficialUrl(currentUrl)
            val connection = currentUrl.openConnection() as HttpsURLConnection
            connection.connectTimeout = 12_000
            connection.readTimeout = 25_000
            connection.requestMethod = "GET"
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("User-Agent", "NOVA-HORIZON/0.1.0-dev (Android)")

            try {
                val status = connection.responseCode
                if (status in 300..399) {
                    if (redirectCount == 3) {
                        throw IllegalStateException("Слишком много перенаправлений Mojang")
                    }
                    val location = connection.getHeaderField("Location")
                        ?: throw IllegalStateException("Перенаправление без адреса")
                    currentUrl = URL(currentUrl, location)
                    validateOfficialUrl(currentUrl)
                    continue
                }
                if (status !in 200..299) {
                    throw IllegalStateException("Сервер Mojang вернул HTTP " + status)
                }

                val contentLength = connection.contentLengthLong
                if (contentLength > maxBytes) {
                    throw IllegalStateException("Ответ Mojang превышает допустимый размер")
                }
                val contentType = connection.contentType.orEmpty()
                if (contentType.isNotBlank() &&
                    !contentType.lowercase(Locale.ROOT).startsWith("application/json")
                ) {
                    throw IllegalStateException("Неожиданный тип ответа Mojang: " + contentType)
                }

                val bytes = connection.inputStream.use { input ->
                    val output = ByteArrayOutputStream(
                        if (contentLength in 1..maxBytes.toLong()) contentLength.toInt() else 32 * 1024
                    )
                    val buffer = ByteArray(16 * 1024)
                    var total = 0
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        total += read
                        if (total > maxBytes) {
                            throw IllegalStateException("Ответ Mojang превышает допустимый размер")
                        }
                        output.write(buffer, 0, read)
                    }
                    output.toByteArray()
                }

                if (contentLength >= 0 && bytes.size.toLong() != contentLength) {
                    throw IllegalStateException("Размер ответа не совпадает с Content-Length")
                }
                if (expectedSha1 != null) {
                    if (!isSha1(expectedSha1)) {
                        throw SecurityException("Некорректная ожидаемая SHA-1")
                    }
                    val actual = sha1(bytes)
                    if (!MessageDigest.isEqual(
                            actual.toByteArray(StandardCharsets.US_ASCII),
                            expectedSha1.lowercase(Locale.ROOT).toByteArray(StandardCharsets.US_ASCII)
                        )
                    ) {
                        throw SecurityException("SHA-1 метаданных версии не совпадает с официальным индексом")
                    }
                }
                return bytes
            } finally {
                connection.disconnect()
            }
        }
        throw IllegalStateException("Не удалось получить данные с официального сервера Mojang")
    }

    private fun validateOfficialUrl(url: URL) {
        val uri = URI(url.toString())
        if (!uri.scheme.equals("https", ignoreCase = true) ||
            !uri.host.equals(OFFICIAL_HOST, ignoreCase = true) ||
            uri.userInfo != null ||
            uri.rawFragment != null ||
            (uri.port != -1 && uri.port != 443)
        ) {
            throw SecurityException("Заблокирован недоверенный адрес метаданных Minecraft")
        }
    }

    private fun isValidVersionId(value: String): Boolean =
        value.isNotEmpty() && value.length <= 64 &&
            value.all {
                it in 'a'..'z' || it in 'A'..'Z' || it in '0'..'9' ||
                    it == '.' || it == '_' || it == '-'
            }

    private fun isSha1(value: String): Boolean =
        value.length == 40 && value.all { it in '0'..'9' || it.lowercaseChar() in 'a'..'f' }

    private fun sha1(bytes: ByteArray): String =
        MessageDigest.getInstance("SHA-1")
            .digest(bytes)
            .joinToString("") { byte ->
                "%02x".format(Locale.ROOT, byte.toInt() and 0xff)
            }
}
