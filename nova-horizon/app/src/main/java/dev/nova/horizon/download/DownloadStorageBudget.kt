package dev.nova.horizon.download

import android.content.Context
import dev.nova.horizon.AssetIndexPlan
import java.io.File
import java.io.IOException
import java.nio.file.Files
import java.security.MessageDigest
import java.util.Locale

/** Preflights real filesystem space; this is not a RAM or game-memory cap. */
internal object DownloadStorageBudget {
    private const val RESERVE_BYTES = 96L * 1024L * 1024L
    private const val HASH_BUFFER_BYTES = 64 * 1024

    fun requireForArtifacts(context: Context, artifacts: List<OfficialArtifactRequest>) {
        val root = minecraftRoot(context)
        var missingBytes = 0L
        artifacts.forEach { artifact ->
            val target = safeChild(root, artifact.relativePath)
            if (!matches(target, artifact.sha1, artifact.size)) {
                missingBytes = Math.addExact(missingBytes, artifact.size)
            }
        }
        requireAvailable(root, missingBytes, 0L, "основные игровые файлы")
    }

    fun requireForAssets(context: Context, plan: AssetIndexPlan) {
        val root = minecraftRoot(context)
        val canHardLink = supportsHardLinks(root)
        var missingObjects = 0L
        var legacyCopies = 0L

        plan.objects.forEach { item ->
            val objectFile = safeChild(root, item.relativePath)
            if (!matches(objectFile, item.hash, item.size)) {
                missingObjects = Math.addExact(missingObjects, item.size)
            }

            if (!canHardLink) {
                item.logicalKeys.forEach { key ->
                    if (plan.virtualAssets) {
                        val target = safeChild(root, "assets/virtual/" + key)
                        if (!matches(target, item.hash, item.size)) {
                            legacyCopies = Math.addExact(legacyCopies, item.size)
                        }
                    }
                    if (plan.mapToResources) {
                        val target = safeChild(root, "resources/" + key)
                        if (!matches(target, item.hash, item.size)) {
                            legacyCopies = Math.addExact(legacyCopies, item.size)
                        }
                    }
                }
            }
        }

        requireAvailable(root, missingObjects, legacyCopies, "ресурсы Minecraft")
    }

    private fun minecraftRoot(context: Context): File =
        File(context.noBackupFilesDir, "nova-horizon/minecraft").apply {
            if (!exists() && !mkdirs()) throw IOException("Не удалось создать каталог Minecraft")
        }.canonicalFile

    private fun safeChild(root: File, relativePath: String): File {
        require(relativePath.isNotBlank() && !relativePath.startsWith('/') &&
            !relativePath.contains('\\') &&
            relativePath.split('/').all { it.isNotBlank() && it != "." && it != ".." })
        val target = File(root, relativePath).canonicalFile
        if (!target.path.startsWith(root.path + File.separator)) {
            throw SecurityException("Путь загрузки выходит за пределы каталога Minecraft")
        }
        return target
    }

    private fun matches(file: File, expectedHash: String, expectedSize: Long): Boolean {
        if (!file.isFile || file.length() != expectedSize) return false
        val digest = MessageDigest.getInstance("SHA-1")
        file.inputStream().buffered().use { input ->
            val buffer = ByteArray(HASH_BUFFER_BYTES)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                digest.update(buffer, 0, read)
            }
        }
        val actual = digest.digest().joinToString("") {
            "%02x".format(Locale.ROOT, it.toInt() and 0xff)
        }
        return actual.equals(expectedHash, ignoreCase = true)
    }

    private fun supportsHardLinks(root: File): Boolean {
        val source = File.createTempFile(".nova-link-check-", ".tmp", root)
        val link = File(root, source.name + ".link")
        return try {
            source.writeBytes(byteArrayOf(0x4e, 0x4f, 0x56))
            Files.createLink(link.toPath(), source.toPath())
            true
        } catch (_: Exception) {
            false
        } finally {
            link.delete()
            source.delete()
        }
    }

    private fun requireAvailable(
        root: File,
        missingBytes: Long,
        legacyCopyBytes: Long,
        label: String
    ) {
        val required = Math.addExact(Math.addExact(missingBytes, legacyCopyBytes), RESERVE_BYTES)
        val available = root.usableSpace
        if (available < required) {
            throw IOException(
                "Недостаточно свободного места для $label. " +
                    "Нужно примерно " + format(required) +
                    ", доступно " + format(available) +
                    " (включая резерв для безопасной записи)."
            )
        }
    }

    private fun format(bytes: Long): String =
        String.format(Locale.ROOT, "%.1f MiB", bytes.toDouble() / (1024.0 * 1024.0))
}
