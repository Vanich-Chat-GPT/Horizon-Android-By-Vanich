package dev.nova.horizon.download

import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import android.os.Build
import android.os.PersistableBundle
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import java.net.URI
import java.security.MessageDigest
import java.util.Locale
import java.util.UUID

internal data class OfficialArtifactRequest(
    val url: String,
    val sha1: String,
    val size: Long,
    val relativePath: String,
    val displayName: String
) {
    fun validate() {
        require(size > 0L) { "Размер файла должен быть положительным" }
        require(sha1.length == 40 && sha1.all { it in '0'..'9' || it.lowercaseChar() in 'a'..'f' }) {
            "Некорректная SHA-1"
        }
        require(relativePath.isNotBlank() && !relativePath.startsWith('/') &&
            !relativePath.contains('\\') && relativePath.split('/').all {
                it.isNotEmpty() && it != "." && it != ".." && it.none { character -> Character.isISOControl(character) }
            }) { "Небезопасный относительный путь" }

        val uri = URI(url)
        val allowedHosts = setOf(
            "piston-data.mojang.com",
            "piston-meta.mojang.com",
            "launcher.mojang.com",
            "libraries.minecraft.net",
            "repo.maven.apache.org"
        )
        val host = uri.host?.lowercase(Locale.ROOT) ?: ""
        require(uri.scheme.equals("https", ignoreCase = true) &&
            host in allowedHosts &&
            uri.userInfo == null && uri.rawFragment == null && uri.rawQuery == null &&
            (uri.port == -1 || uri.port == 443)
        ) { "Источник файла не входит в список разрешённых HTTPS-хостов" }
    }

    internal fun toWorkData() = androidx.work.workDataOf(
        KEY_URL to url,
        KEY_SHA1 to sha1,
        KEY_SIZE to size,
        KEY_PATH to relativePath,
        KEY_NAME to displayName
    )

    internal fun toPersistableBundle() = PersistableBundle().apply {
        putString(KEY_URL, url)
        putString(KEY_SHA1, sha1)
        putLong(KEY_SIZE, size)
        putString(KEY_PATH, relativePath)
        putString(KEY_NAME, displayName)
    }

    companion object {
        const val KEY_URL = "artifact_url"
        const val KEY_SHA1 = "artifact_sha1"
        const val KEY_SIZE = "artifact_size"
        const val KEY_PATH = "artifact_path"
        const val KEY_NAME = "artifact_name"

        fun fromWorkData(data: androidx.work.Data): OfficialArtifactRequest? =
            runCatching {
                OfficialArtifactRequest(
                    data.getString(KEY_URL) ?: error("Missing URL"),
                    data.getString(KEY_SHA1) ?: error("Missing SHA-1"),
                    data.getLong(KEY_SIZE, -1L),
                    data.getString(KEY_PATH) ?: error("Missing path"),
                    data.getString(KEY_NAME) ?: "Minecraft file"
                ).also { it.validate() }
            }.getOrNull()

        fun fromPersistableBundle(bundle: PersistableBundle): OfficialArtifactRequest? =
            runCatching {
                OfficialArtifactRequest(
                    bundle.getString(KEY_URL) ?: error("Missing URL"),
                    bundle.getString(KEY_SHA1) ?: error("Missing SHA-1"),
                    bundle.getLong(KEY_SIZE, -1L),
                    bundle.getString(KEY_PATH) ?: error("Missing path"),
                    bundle.getString(KEY_NAME) ?: "Minecraft file"
                ).also { it.validate() }
            }.getOrNull()
    }
}

internal data class DownloadHandle(val value: String)

internal object DownloadCoordinator {
    fun enqueue(context: Context, request: OfficialArtifactRequest): DownloadHandle {
        request.validate()

        val active = DownloadProgressStore.all(context).firstOrNull {
            it.path == request.relativePath &&
                (it.state == "QUEUED" || it.state == "RUNNING" || it.state == "RETRYING") &&
                it.handle.isNotBlank()
        }
        if (active != null) return DownloadHandle(active.handle)

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            val jobId = stableJobId(request.relativePath)
            val handle = "job:" + jobId
            DownloadProgressStore.enqueue(context, request, handle)
            try {
                enqueueUserInitiated(context, request, jobId)
                DownloadHandle(handle)
            } catch (failure: Exception) {
                DownloadProgressStore.updateByHandle(
                    context, handle, "FAILED", failure.message ?: "Android отклонил загрузку"
                )
                throw failure
            }
        } else {
            val work = buildWorkRequest(request)
            val handle = "work:" + work.id
            DownloadProgressStore.enqueue(context, request, handle)
            try {
                val stable = stableKey(request.relativePath)
                WorkManager.getInstance(context).enqueueUniqueWork(
                    "nova-artifact-" + stable,
                    ExistingWorkPolicy.KEEP,
                    work
                )
                DownloadHandle(handle)
            } catch (failure: Exception) {
                DownloadProgressStore.updateByHandle(
                    context, handle, "FAILED", failure.message ?: "WorkManager отклонил загрузку"
                )
                throw failure
            }
        }
    }

    fun cancel(context: Context, handle: DownloadHandle) {
        val separator = handle.value.indexOf(':')
        if (separator <= 0) return
        val kind = handle.value.substring(0, separator)
        val id = handle.value.substring(separator + 1)
        when (kind) {
            "job" -> id.toIntOrNull()?.let {
                (context.getSystemService(Context.JOB_SCHEDULER_SERVICE) as JobScheduler).cancel(it)
            }
            "work" -> runCatching {
                WorkManager.getInstance(context).cancelWorkById(UUID.fromString(id))
            }
        }
        DownloadProgressStore.updateByHandle(context, handle.value, "CANCELLED")
    }

    private fun buildWorkRequest(request: OfficialArtifactRequest) =
        OneTimeWorkRequestBuilder<OfficialArtifactDownloadWorker>()
            .setInputData(request.toWorkData())
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .addTag("nova-artifact-" + stableKey(request.relativePath))
            .build()

    private fun enqueueUserInitiated(context: Context, request: OfficialArtifactRequest, jobId: Int) {
        val scheduler = context.getSystemService(Context.JOB_SCHEDULER_SERVICE) as JobScheduler
        val job = JobInfo.Builder(
            jobId,
            ComponentName(context, ArtifactDownloadJobService::class.java)
        )
            .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setUserInitiated(true)
            .setEstimatedNetworkBytes(request.size, 0L)
            .setExtras(request.toPersistableBundle())
            .build()

        val result = scheduler.schedule(job)
        check(result == JobScheduler.RESULT_SUCCESS) {
            "Android не принял пользовательскую задачу загрузки (код " + result + ")"
        }
    }

    private fun stableKey(path: String): String =
        MessageDigest.getInstance("SHA-256")
            .digest(path.toByteArray(Charsets.UTF_8))
            .take(10)
            .joinToString("") { "%02x".format(Locale.ROOT, it.toInt() and 0xff) }

    private fun stableJobId(path: String): Int {
        val digest = MessageDigest.getInstance("SHA-256").digest(path.toByteArray(Charsets.UTF_8))
        val raw = ((digest[0].toInt() and 0xff) shl 24) or
            ((digest[1].toInt() and 0xff) shl 16) or
            ((digest[2].toInt() and 0xff) shl 8) or
            (digest[3].toInt() and 0xff)
        return 100_000 + (raw and 0x3fff_ffff)
    }
}
