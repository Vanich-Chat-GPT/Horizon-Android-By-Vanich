package dev.nova.horizon.download

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.nio.file.AtomicMoveNotSupportedException
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.MessageDigest
import java.util.Locale

/**
 * Materializes the legacy asset layouts described by Mojang's asset index.
 * The content-addressed object store remains the canonical source of truth.
 */
internal object AssetMaterializer {
    private const val COPY_BUFFER_BYTES = 64 * 1024
    private const val FREE_SPACE_MARGIN_BYTES = 1024L * 1024L

    fun materialize(context: Context, manifest: JSONObject) {
        val virtualAssets = manifest.optBoolean("virtualAssets", false)
        val mapToResources = manifest.optBoolean("mapToResources", false)
        if (!virtualAssets && !mapToResources) return

        val root = File(context.noBackupFilesDir, "nova-horizon/minecraft").canonicalFile
        val objects = manifest.getJSONArray("objects")

        for (index in 0 until objects.length()) {
            val item = objects.getJSONObject(index)
            val source = safeChild(root, item.getString("relativePath"))
            if (!source.isFile) {
                throw IOException("Не найден скачанный asset object: " + item.getString("hash"))
            }
            val expectedHash = item.getString("hash")
            val expectedSize = item.getLong("size")
            if (source.length() != expectedSize ||
                !hashFile(source).equals(expectedHash, ignoreCase = true)
            ) {
                throw SecurityException("Asset object изменился после проверки SHA-1")
            }

            val keys = item.getJSONArray("logicalKeys")
            for (keyIndex in 0 until keys.length()) {
                val logicalKey = keys.getString(keyIndex)
                if (virtualAssets) {
                    linkOrCopy(root, source, safeChild(root, "assets/virtual/" + logicalKey))
                }
                if (mapToResources) {
                    linkOrCopy(root, source, safeChild(root, "resources/" + logicalKey))
                }
            }
        }
    }

    private fun safeChild(root: File, relativePath: String): File {
        require(relativePath.isNotBlank() && !relativePath.startsWith('/') &&
            !relativePath.contains('\\') &&
            relativePath.split('/').all { it.isNotBlank() && it != "." && it != ".." }) {
            "Небезопасный путь ресурса"
        }
        val result = File(root, relativePath).canonicalFile
        if (!result.path.startsWith(root.path + File.separator)) {
            throw SecurityException("Путь ресурса выходит за пределы каталога Minecraft")
        }
        return result
    }

    private fun linkOrCopy(root: File, source: File, target: File) {
        val parent = target.parentFile ?: throw IOException("У ресурса отсутствует родительский каталог")
        if (!parent.exists() && !parent.mkdirs()) {
            throw IOException("Не удалось создать каталог legacy-ресурсов")
        }
        val safeTarget = target.canonicalFile
        if (!safeTarget.path.startsWith(root.path + File.separator)) {
            throw SecurityException("Целевой ресурс выходит за пределы каталога Minecraft")
        }
        if (safeTarget.isFile &&
            safeTarget.length() == source.length() &&
            hashFile(safeTarget) == hashFile(source)
        ) {
            return
        }

        val temporary = File(parent, safeTarget.name + ".nova-tmp")
        if (temporary.exists() && !temporary.delete()) {
            throw IOException("Не удалось удалить временный legacy-файл")
        }

        var linked = false
        try {
            Files.createLink(temporary.toPath(), source.toPath())
            linked = true
        } catch (_: Exception) {
            val required = source.length().coerceAtLeast(0L) + FREE_SPACE_MARGIN_BYTES
            if (parent.usableSpace < required) {
                throw IOException("Недостаточно места для материализации legacy-ресурсов")
            }
            source.inputStream().buffered().use { input ->
                FileOutputStream(temporary).use { output ->
                    val buffer = ByteArray(COPY_BUFFER_BYTES)
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        output.write(buffer, 0, read)
                    }
                    output.fd.sync()
                }
            }
        }

        try {
            Files.move(
                temporary.toPath(),
                safeTarget.toPath(),
                StandardCopyOption.ATOMIC_MOVE,
                StandardCopyOption.REPLACE_EXISTING
            )
        } catch (_: AtomicMoveNotSupportedException) {
            Files.move(
                temporary.toPath(),
                safeTarget.toPath(),
                StandardCopyOption.REPLACE_EXISTING
            )
        } catch (failure: Exception) {
            if (linked) temporary.delete()
            throw failure
        }
    }

    private fun hashFile(file: File): String {
        val digest = MessageDigest.getInstance("SHA-1")
        file.inputStream().buffered().use { input ->
            val buffer = ByteArray(COPY_BUFFER_BYTES)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") {
            "%02x".format(Locale.ROOT, it.toInt() and 0xff)
        }
    }
}
