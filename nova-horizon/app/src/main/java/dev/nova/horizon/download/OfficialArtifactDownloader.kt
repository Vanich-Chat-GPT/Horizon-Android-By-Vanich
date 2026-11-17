package dev.nova.horizon.download

import android.content.Context
import android.os.SystemClock
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.nio.file.AtomicMoveNotSupportedException
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.Locale
import javax.net.ssl.HttpsURLConnection

internal data class ArtifactDownloadResult(
    val file: File,
    val downloadedBytes: Long,
    val alreadyPresent: Boolean
)

internal object OfficialArtifactDownloader {
    private const val CONNECT_TIMEOUT_MS = 15_000
    private const val READ_TIMEOUT_MS = 30_000
    private const val PROGRESS_INTERVAL_MS = 500L
    private val allowedHosts = setOf(
        "piston-data.mojang.com",
        "piston-meta.mojang.com",
        "launcher.mojang.com",
        "libraries.minecraft.net",
        "repo.maven.apache.org"
    )

    suspend fun download(
        context: Context,
        request: OfficialArtifactRequest,
        onProgress: suspend (downloaded: Long, total: Long, bytesPerSecond: Long) -> Unit
    ): ArtifactDownloadResult = withContext(Dispatchers.IO) {
        request.validate()
        val root = File(context.noBackupFilesDir, "nova-horizon/minecraft").apply {
            if (!exists() && !mkdirs()) throw IOException("Не удалось создать каталог игры")
        }.canonicalFile

        val target = File(root, request.relativePath).canonicalFile
        if (!target.path.startsWith(root.path + File.separator)) {
            throw SecurityException("Путь файла выходит за пределы каталога Minecraft")
        }
        val parent = target.parentFile ?: throw IOException("У файла отсутствует каталог")
        if (!parent.exists() && !parent.mkdirs()) {
            throw IOException("Не удалось создать каталог назначения")
        }

        if (target.isFile && target.length() == request.size &&
            hashFile(target).equals(request.sha1, ignoreCase = true)
        ) {
            onProgress(request.size, request.size, 0L)
            return@withContext ArtifactDownloadResult(target, request.size, true)
        }

        val part = File(parent, target.name + ".part")
        val etagFile = File(parent, target.name + ".part.etag")
        var offset = if (part.isFile) part.length() else 0L
        var etag = etagFile.takeIf { it.isFile }?.readText()?.trim()?.takeIf(::isStrongEtag)

        if (offset <= 0L || offset >= request.size || etag == null) {
            part.delete()
            etagFile.delete()
            offset = 0L
            etag = null
        }

        val requiredSpace = (request.size - offset).coerceAtLeast(0L) + 1024L * 1024L
        if (parent.usableSpace < requiredSpace) {
            throw IOException("Недостаточно свободного места для загрузки файла")
        }

        var connection = openConnection(request.url, offset, etag)
        try {
            var status = connection.responseCode
            if (offset > 0L && status == 416) {
                connection.disconnect()
                part.delete()
                etagFile.delete()
                offset = 0L
                etag = null
                connection = openConnection(request.url, 0L, null)
                status = connection.responseCode
            }

            var append = false
            if (offset > 0L && status == HttpURLConnection.HTTP_PARTIAL) {
                val responseEtag = connection.getHeaderField("ETag")
                if (responseEtag == null || responseEtag != etag || !isStrongEtag(responseEtag)) {
                    connection.disconnect()
                    part.delete()
                    etagFile.delete()
                    offset = 0L
                    etag = null
                    connection = openConnection(request.url, 0L, null)
                    status = connection.responseCode
                } else {
                    validateContentRange(connection.getHeaderField("Content-Range"), offset, request.size)
                    append = true
                }
            }

            if (status != HttpURLConnection.HTTP_OK && !(append && status == HttpURLConnection.HTTP_PARTIAL)) {
                throw IOException("Сервер артефакта вернул HTTP " + status)
            }

            if (!append) offset = 0L
            val expectedResponseBytes = request.size - offset
            val responseLength = connection.contentLengthLong
            if (responseLength >= 0L && responseLength != expectedResponseBytes) {
                throw IOException("Content-Length не совпадает с размером из официальных метаданных")
            }

            val responseEtag = connection.getHeaderField("ETag")
            if (isStrongEtag(responseEtag)) {
                writeTextAtomically(etagFile, responseEtag!!)
            } else {
                etagFile.delete()
            }

            val digest = MessageDigest.getInstance("SHA-1")
            if (append) {
                part.inputStream().buffered().use { input ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        currentCoroutineContext().ensureActive()
                        val read = input.read(buffer)
                        if (read < 0) break
                        digest.update(buffer, 0, read)
                    }
                }
            }

            var downloaded = offset
            var lastReportTime = SystemClock.elapsedRealtime()
            var lastReportBytes = downloaded
            FileOutputStream(part, append).use { output ->
                connection.inputStream.use { input ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        currentCoroutineContext().ensureActive()
                        val read = input.read(buffer)
                        if (read < 0) break
                        downloaded += read
                        if (downloaded > request.size) {
                            throw IOException("Сервер передал больше байт, чем заявлено в метаданных")
                        }
                        output.write(buffer, 0, read)
                        digest.update(buffer, 0, read)

                        val now = SystemClock.elapsedRealtime()
                        if (now - lastReportTime >= PROGRESS_INTERVAL_MS) {
                            val elapsed = (now - lastReportTime).coerceAtLeast(1L)
                            val speed = ((downloaded - lastReportBytes) * 1000L) / elapsed
                            onProgress(downloaded, request.size, speed)
                            lastReportTime = now
                            lastReportBytes = downloaded
                        }
                    }
                }
                output.fd.sync()
            }

            if (downloaded != request.size || part.length() != request.size) {
                throw IOException("Загружено " + downloaded + " байт из " + request.size)
            }

            val actualSha1 = digest.digest().toHex()
            if (!MessageDigest.isEqual(
                    actualSha1.toByteArray(Charsets.US_ASCII),
                    request.sha1.lowercase(Locale.ROOT).toByteArray(Charsets.US_ASCII)
                )
            ) {
                part.delete()
                etagFile.delete()
                throw SecurityException("SHA-1 загруженного файла не совпадает с официальными метаданными")
            }

            moveAtomically(part, target)
            etagFile.delete()
            onProgress(request.size, request.size, 0L)
            ArtifactDownloadResult(target, request.size, false)
        } finally {
            connection.disconnect()
        }
    }

    private fun openConnection(address: String, offset: Long, etag: String?): HttpsURLConnection {
        var current = URL(address)
        for (redirect in 0..3) {
            validateUrl(current)
            val connection = current.openConnection() as HttpsURLConnection
            connection.connectTimeout = CONNECT_TIMEOUT_MS
            connection.readTimeout = READ_TIMEOUT_MS
            connection.requestMethod = "GET"
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Accept-Encoding", "identity")
            connection.setRequestProperty("Cache-Control", "no-transform")
            connection.setRequestProperty("User-Agent", "NOVA-HORIZON/0.1.0-dev (Android)")
            if (offset > 0L) {
                connection.setRequestProperty("Range", "bytes=" + offset + "-")
                if (etag != null) connection.setRequestProperty("If-Range", etag)
            }

            val status = connection.responseCode
            if (status in 300..399) {
                if (redirect == 3) {
                    connection.disconnect()
                    throw IOException("Слишком много перенаправлений файлового сервера")
                }
                val location = connection.getHeaderField("Location")
                    ?: run {
                        connection.disconnect()
                        throw IOException("Перенаправление без адреса")
                    }
                val next = URL(current, location)
                connection.disconnect()
                validateUrl(next)
                current = next
            } else {
                return connection
            }
        }
        throw IOException("Не удалось открыть официальный файловый сервер")
    }

    private fun validateUrl(url: URL) {
        val uri = URI(url.toString())
        val host = uri.host?.lowercase(Locale.ROOT) ?: ""
        if (!uri.scheme.equals("https", ignoreCase = true) ||
            host !in allowedHosts ||
            uri.userInfo != null || uri.rawFragment != null || uri.rawQuery != null ||
            (uri.port != -1 && uri.port != 443)
        ) {
            throw SecurityException("Заблокирован недоверенный URL загрузки")
        }
    }

    private fun validateContentRange(value: String?, expectedStart: Long, expectedTotal: Long) {
        val match = Regex("^bytes (\\d+)-(\\d+)/(\\d+)$").matchEntire(value ?: "")
            ?: throw IOException("Некорректный Content-Range при возобновлении")
        val start = match.groupValues[1].toLong()
        val end = match.groupValues[2].toLong()
        val total = match.groupValues[3].toLong()
        if (start != expectedStart || end < start || total != expectedTotal || end >= total) {
            throw IOException("Content-Range не совпадает с ожидаемым диапазоном")
        }
    }

    private fun isStrongEtag(value: String?): Boolean =
        !value.isNullOrBlank() && !value.startsWith("W/", ignoreCase = true)

    private fun hashFile(file: File): String {
        val digest = MessageDigest.getInstance("SHA-1")
        file.inputStream().buffered().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().toHex()
    }

    private fun writeTextAtomically(target: File, value: String) {
        val temp = File(target.parentFile, target.name + ".tmp")
        FileOutputStream(temp).use { output ->
            output.write(value.toByteArray(Charsets.UTF_8))
            output.fd.sync()
        }
        moveAtomically(temp, target)
    }

    private fun moveAtomically(source: File, target: File) {
        try {
            Files.move(
                source.toPath(),
                target.toPath(),
                StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING
            )
        } catch (_: AtomicMoveNotSupportedException) {
            Files.move(source.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING)
        }
    }

    private fun ByteArray.toHex(): String =
        joinToString("") { "%02x".format(Locale.ROOT, it.toInt() and 0xff) }
}
