package dev.nova.horizon.download

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONObject
import java.security.MessageDigest
import java.util.Locale

internal data class DownloadProgressEntry(
    val path: String,
    val displayName: String,
    val state: String,
    val downloadedBytes: Long,
    val totalBytes: Long,
    val bytesPerSecond: Long,
    val handle: String,
    val error: String,
    val updatedAt: Long
) {
    val percent: Int
        get() = if (totalBytes > 0L) {
            ((downloadedBytes.coerceAtMost(totalBytes) * 100L) / totalBytes).toInt().coerceIn(0, 100)
        } else {
            0
        }
}

internal object DownloadProgressStore {
    private const val PREFERENCES = "nova_download_progress_v1"
    private const val PREFIX = "task_"
    private const val MAX_RECORDS = 120

    private fun preferences(context: Context): SharedPreferences =
        context.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)

    @Synchronized
    fun enqueue(context: Context, request: OfficialArtifactRequest, handle: String) {
        val old = read(context, request.relativePath)
        write(
            context,
            DownloadProgressEntry(
                path = request.relativePath,
                displayName = request.displayName,
                state = "QUEUED",
                downloadedBytes = old?.downloadedBytes ?: 0L,
                totalBytes = request.size,
                bytesPerSecond = 0L,
                handle = handle,
                error = "",
                updatedAt = System.currentTimeMillis()
            )
        )
    }

    @Synchronized
    fun update(
        context: Context,
        request: OfficialArtifactRequest,
        state: String,
        downloadedBytes: Long? = null,
        bytesPerSecond: Long? = null,
        error: String? = null
    ) {
        val old = read(context, request.relativePath)
        write(
            context,
            DownloadProgressEntry(
                path = request.relativePath,
                displayName = request.displayName,
                state = state,
                downloadedBytes = (downloadedBytes ?: old?.downloadedBytes ?: 0L)
                    .coerceIn(0L, request.size),
                totalBytes = request.size,
                bytesPerSecond = (bytesPerSecond ?: 0L).coerceAtLeast(0L),
                handle = old?.handle.orEmpty(),
                error = error.orEmpty().take(512),
                updatedAt = System.currentTimeMillis()
            )
        )
    }

    @Synchronized
    fun enqueueAggregate(
        context: Context,
        path: String,
        displayName: String,
        totalBytes: Long,
        handle: String
    ) {
        require(path.isNotBlank() && !path.startsWith('/') && !path.contains('\\'))
        val old = read(context, path)
        write(
            context,
            DownloadProgressEntry(
                path = path,
                displayName = displayName,
                state = "QUEUED",
                downloadedBytes = old?.downloadedBytes?.coerceAtMost(totalBytes) ?: 0L,
                totalBytes = totalBytes.coerceAtLeast(0L),
                bytesPerSecond = 0L,
                handle = handle,
                error = "",
                updatedAt = System.currentTimeMillis()
            )
        )
    }

    @Synchronized
    fun updateAggregate(
        context: Context,
        path: String,
        displayName: String,
        state: String,
        downloadedBytes: Long,
        totalBytes: Long,
        bytesPerSecond: Long = 0L,
        error: String = ""
    ) {
        write(
            context,
            DownloadProgressEntry(
                path = path,
                displayName = displayName,
                state = state,
                downloadedBytes = downloadedBytes.coerceIn(0L, totalBytes.coerceAtLeast(0L)),
                totalBytes = totalBytes.coerceAtLeast(0L),
                bytesPerSecond = bytesPerSecond.coerceAtLeast(0L),
                handle = read(context, path)?.handle.orEmpty(),
                error = error.take(512),
                updatedAt = System.currentTimeMillis()
            )
        )
    }

    @Synchronized
    fun findByHandle(context: Context, handle: String): DownloadProgressEntry? =
        all(context).firstOrNull { it.handle == handle }

    @Synchronized
    fun updateByHandle(
        context: Context,
        handle: String,
        state: String,
        error: String = ""
    ) {
        val old = findByHandle(context, handle) ?: return
        write(context, old.copy(
            state = state,
            bytesPerSecond = 0L,
            error = error.take(512),
            updatedAt = System.currentTimeMillis()
        ))
    }

    @Synchronized
    fun all(context: Context): List<DownloadProgressEntry> {
        return preferences(context).all.entries
            .asSequence()
            .filter { it.key.startsWith(PREFIX) && it.value is String }
            .mapNotNull { entry ->
                runCatching { fromJson(entry.value as String) }.getOrNull()
            }
            .sortedByDescending { it.updatedAt }
            .take(MAX_RECORDS)
            .toList()
    }

    @Synchronized
    fun clearFinished(context: Context) {
        val editor = preferences(context).edit()
        all(context)
            .filter { it.state == "COMPLETE" || it.state == "CANCELLED" || it.state == "FAILED" }
            .forEach { editor.remove(key(it.path)) }
        editor.apply()
    }

    private fun read(context: Context, path: String): DownloadProgressEntry? =
        preferences(context).getString(key(path), null)?.let { value ->
            runCatching { fromJson(value) }.getOrNull()
        }

    private fun write(context: Context, entry: DownloadProgressEntry) {
        preferences(context).edit().putString(key(entry.path), toJson(entry).toString()).apply()
        prune(context)
    }

    private fun prune(context: Context) {
        val records = all(context)
        if (records.size < MAX_RECORDS) return
        val keep = records.take(MAX_RECORDS - 1).map { key(it.path) }.toSet()
        val editor = preferences(context).edit()
        preferences(context).all.keys
            .filter { it.startsWith(PREFIX) && it !in keep }
            .forEach(editor::remove)
        editor.apply()
    }

    private fun key(path: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(path.toByteArray(Charsets.UTF_8))
        val short = digest.take(16).joinToString("") {
            "%02x".format(Locale.ROOT, it.toInt() and 0xff)
        }
        return PREFIX + short
    }

    private fun toJson(entry: DownloadProgressEntry) = JSONObject().apply {
        put("path", entry.path)
        put("displayName", entry.displayName)
        put("state", entry.state)
        put("downloadedBytes", entry.downloadedBytes)
        put("totalBytes", entry.totalBytes)
        put("bytesPerSecond", entry.bytesPerSecond)
        put("handle", entry.handle)
        put("error", entry.error)
        put("updatedAt", entry.updatedAt)
    }

    private fun fromJson(json: String): DownloadProgressEntry {
        val value = JSONObject(json)
        return DownloadProgressEntry(
            path = value.getString("path"),
            displayName = value.getString("displayName"),
            state = value.getString("state"),
            downloadedBytes = value.optLong("downloadedBytes", 0L),
            totalBytes = value.optLong("totalBytes", 0L),
            bytesPerSecond = value.optLong("bytesPerSecond", 0L),
            handle = value.optString("handle"),
            error = value.optString("error"),
            updatedAt = value.optLong("updatedAt", 0L)
        )
    }
}
