package dev.nova.horizon.download

import android.app.job.JobInfo
import android.app.job.JobParameters
import android.app.job.JobScheduler
import android.app.job.JobService
import android.content.ComponentName
import android.content.Context
import android.os.Build
import android.os.PersistableBundle
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.ForegroundInfo
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.net.URI
import java.security.MessageDigest
import java.util.Locale
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

internal data class AssetBatchRequest(
    val versionId: String,
    val manifestPath: String,
    val progressPath: String,
    val totalBytes: Long,
    val objectCount: Int
) {
    fun validate() {
        require(versionId.isNotBlank() && versionId.length <= 64 &&
            versionId.all { it.isLetterOrDigit() || it == '.' || it == '_' || it == '-' })
        require(manifestPath.startsWith("manifests/") &&
            !manifestPath.startsWith('/') && !manifestPath.contains('\\') &&
            manifestPath.split('/').all { it.isNotBlank() && it != "." && it != ".." })
        require(progressPath.startsWith("asset-batches/") &&
            !progressPath.contains('\\') &&
            progressPath.split('/').all { it.isNotBlank() && it != "." && it != ".." })
        require(totalBytes > 0L)
        require(objectCount in 1..150_000)
    }

    fun toWorkData() = workDataOf(
        KEY_VERSION to versionId,
        KEY_MANIFEST to manifestPath,
        KEY_PROGRESS to progressPath,
        KEY_TOTAL to totalBytes,
        KEY_COUNT to objectCount
    )

    fun toBundle() = PersistableBundle().apply {
        putString(KEY_VERSION, versionId)
        putString(KEY_MANIFEST, manifestPath)
        putString(KEY_PROGRESS, progressPath)
        putLong(KEY_TOTAL, totalBytes)
        putInt(KEY_COUNT, objectCount)
    }

    companion object {
        const val KEY_VERSION = "asset_batch_version"
        const val KEY_MANIFEST = "asset_batch_manifest"
        const val KEY_PROGRESS = "asset_batch_progress"
        const val KEY_TOTAL = "asset_batch_total"
        const val KEY_COUNT = "asset_batch_count"

        fun fromWorkData(data: androidx.work.Data): AssetBatchRequest? = runCatching {
            AssetBatchRequest(
                data.getString(KEY_VERSION) ?: error("Missing version"),
                data.getString(KEY_MANIFEST) ?: error("Missing manifest"),
                data.getString(KEY_PROGRESS) ?: error("Missing progress path"),
                data.getLong(KEY_TOTAL, -1L),
                data.getInt(KEY_COUNT, -1)
            ).also { it.validate() }
        }.getOrNull()

        fun fromBundle(bundle: PersistableBundle): AssetBatchRequest? = runCatching {
            AssetBatchRequest(
                bundle.getString(KEY_VERSION) ?: error("Missing version"),
                bundle.getString(KEY_MANIFEST) ?: error("Missing manifest"),
                bundle.getString(KEY_PROGRESS) ?: error("Missing progress path"),
                bundle.getLong(KEY_TOTAL, -1L),
                bundle.getInt(KEY_COUNT, -1)
            ).also { it.validate() }
        }.getOrNull()
    }
}

internal object AssetBatchManifest {
    private const val MAX_MANIFEST_BYTES = 32L * 1024L * 1024L

    fun write(context: Context, versionId: String, plan: dev.nova.horizon.AssetIndexPlan): String {
        require(plan.objects.isNotEmpty() && plan.objects.size <= 150_000)
        val root = File(context.noBackupFilesDir, "nova-horizon").apply {
            if (!exists() && !mkdirs()) throw IOException("Не удалось создать каталог NOVA")
        }.canonicalFile
        val directory = File(root, "manifests").apply {
            if (!exists() && !mkdirs()) throw IOException("Не удалось создать каталог манифестов")
        }.canonicalFile
        if (!directory.path.startsWith(root.path + File.separator)) {
            throw SecurityException("Каталог манифестов выходит за пределы NOVA")
        }

        val objects = JSONArray()
        plan.objects.forEach { item ->
            objects.put(JSONObject().apply {
                put("hash", item.hash)
                put("size", item.size)
                put("url", item.url)
                put("relativePath", item.relativePath)
                put("logicalKeys", JSONArray(item.logicalKeys))
            })
        }
        val json = JSONObject().apply {
            put("versionId", versionId)
            put("assetIndexId", plan.assetIndexId)
            put("totalDownloadBytes", plan.totalDownloadBytes)
            put("virtualAssets", plan.virtualAssets)
            put("mapToResources", plan.mapToResources)
            put("objects", objects)
        }.toString()

        if (json.toByteArray(Charsets.UTF_8).size.toLong() > MAX_MANIFEST_BYTES) {
            throw IOException("Манифест ресурсов превышает допустимый размер")
        }

        val name = "assets-" + sha256(versionId).take(24) + ".json"
        val target = File(directory, name)
        val temp = File(directory, name + ".tmp")
        FileOutputStream(temp).use { output ->
            output.write(json.toByteArray(Charsets.UTF_8))
            output.fd.sync()
        }
        try {
            java.nio.file.Files.move(
                temp.toPath(),
                target.toPath(),
                java.nio.file.StandardCopyOption.ATOMIC_MOVE,
                java.nio.file.StandardCopyOption.REPLACE_EXISTING
            )
        } catch (_: java.nio.file.AtomicMoveNotSupportedException) {
            java.nio.file.Files.move(
                temp.toPath(),
                target.toPath(),
                java.nio.file.StandardCopyOption.REPLACE_EXISTING
            )
        }
        return "manifests/" + name
    }

    internal fun sha256(value: String): String =
        MessageDigest.getInstance("SHA-256")
            .digest(value.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(Locale.ROOT, it.toInt() and 0xff) }
}

internal object AssetBatchRunner {
    private const val MAX_MANIFEST_BYTES = 32L * 1024L * 1024L

    suspend fun run(
        context: Context,
        request: AssetBatchRequest,
        onProgress: suspend (downloaded: Long, total: Long, speed: Long) -> Unit
    ) = withContext(Dispatchers.IO) {
        request.validate()
        val root = File(context.noBackupFilesDir, "nova-horizon").canonicalFile
        val manifest = File(root, request.manifestPath).canonicalFile
        if (!manifest.path.startsWith(root.path + File.separator) ||
            !manifest.isFile || manifest.length() !in 1..MAX_MANIFEST_BYTES
        ) {
            throw SecurityException("Манифест ресурсов отсутствует или недопустим")
        }

        val document = JSONObject(manifest.readText(Charsets.UTF_8))
        if (document.getString("versionId") != request.versionId) {
            throw SecurityException("Версия манифеста не совпадает с заданием")
        }
        val objects = document.getJSONArray("objects")
        if (objects.length() != request.objectCount || objects.length() !in 1..150_000) {
            throw SecurityException("Количество ресурсов не совпадает с заданием")
        }

        val total = document.getLong("totalDownloadBytes")
        if (total != request.totalBytes) {
            throw SecurityException("Размер ресурсов не совпадает с заданием")
        }

        var completed = 0L
        val progressMutex = Mutex()
        val parallelism = 4

        for (start in 0 until objects.length() step parallelism) {
            currentCoroutineContext().ensureActive()
            val endExclusive = minOf(start + parallelism, objects.length())
            val batchBase = completed
            val inFlight = ConcurrentHashMap<Int, Long>()
            val speeds = ConcurrentHashMap<Int, Long>()
            var batchBytes = 0L

            for (index in start until endExclusive) {
                batchBytes = Math.addExact(batchBytes, objects.getJSONObject(index).getLong("size"))
            }

            coroutineScope {
                (start until endExclusive).map { index ->
                    async(Dispatchers.IO) {
                        val item = objects.getJSONObject(index)
                        val requestForObject = OfficialArtifactRequest(
                            url = item.getString("url"),
                            sha1 = item.getString("hash"),
                            size = item.getLong("size"),
                            relativePath = item.getString("relativePath"),
                            displayName = request.versionId + " · ресурс " + (index + 1) + "/" + objects.length()
                        ).also { it.validate() }

                        OfficialArtifactDownloader.download(context, requestForObject) { downloaded, _, speed ->
                            inFlight[index] = downloaded
                            speeds[index] = speed
                            progressMutex.withLock {
                                val activeBytes = inFlight.values.sum()
                                val aggregateSpeed = speeds.values.sum()
                                onProgress((batchBase + activeBytes).coerceAtMost(total), total, aggregateSpeed)
                            }
                        }
                    }
                }.awaitAll()
            }

            completed = Math.addExact(completed, batchBytes)
            onProgress(completed, total, 0L)
        }

        if (completed != total) {
            throw IOException("Итоговый размер загруженных ресурсов не совпал с манифестом")
        }

        AssetMaterializer.materialize(context, document)
        completed
    }
}

internal object AssetBatchCoordinator {
    fun prepareAndEnqueue(context: Context, plan: dev.nova.horizon.AndroidInstallPlan): AssetBatchScheduleResult {
        val account = dev.nova.horizon.account.MinecraftAccountStore.read(context)
        check(account.hasJavaEntitlement) {
            "Сначала подтвердите право на Minecraft: Java Edition через Microsoft."
        }

        val assetIndexId = plan.assetIndex.relativePath
            .substringAfterLast('/')
            .removeSuffix(".json")
        require(assetIndexId.isNotBlank()) { "Не удалось определить ID asset index" }

        val indexRequest = OfficialArtifactRequest(
            url = plan.assetIndex.url,
            sha1 = plan.assetIndex.sha1,
            size = plan.assetIndex.size,
            relativePath = plan.assetIndex.relativePath,
            displayName = plan.versionId + " · asset index"
        ).also { it.validate() }

        val indexEntry = DownloadProgressStore.all(context)
            .firstOrNull { it.path == indexRequest.relativePath }
        check(indexEntry == null || indexEntry.state !in setOf("QUEUED", "RUNNING", "RETRYING")) {
            "Asset index уже загружается. Дождитесь завершения и повторите действие."
        }

        DownloadProgressStore.enqueue(context, indexRequest, "index:" + plan.versionId)
        DownloadProgressStore.update(context, indexRequest, "RUNNING", downloadedBytes = 0L)
        val downloadedIndex = try {
            kotlinx.coroutines.runBlocking {
                OfficialArtifactDownloader.download(context, indexRequest) { downloaded, _, speed ->
                    DownloadProgressStore.update(
                        context, indexRequest, "RUNNING", downloadedBytes = downloaded, bytesPerSecond = speed
                    )
                }
            }
        } catch (failure: Exception) {
            DownloadProgressStore.update(
                context, indexRequest, "FAILED",
                error = failure.message ?: "Не удалось получить asset index"
            )
            throw failure
        }
        DownloadProgressStore.update(
            context, indexRequest, "COMPLETE", downloadedBytes = indexRequest.size
        )

        val assetPlan = dev.nova.horizon.AssetIndexRepository.parse(downloadedIndex.file, assetIndexId)
        DownloadStorageBudget.requireForAssets(context, assetPlan)
        val manifestPath = AssetBatchManifest.write(context, plan.versionId, assetPlan)
        val request = AssetBatchRequest(
            versionId = plan.versionId,
            manifestPath = manifestPath,
            progressPath = "asset-batches/" + plan.versionId,
            totalBytes = assetPlan.totalDownloadBytes,
            objectCount = assetPlan.objects.size
        )
        request.validate()

        val active = DownloadProgressStore.all(context).firstOrNull {
            it.path == request.progressPath &&
                it.state in setOf("QUEUED", "RUNNING", "RETRYING") &&
                it.handle.isNotBlank()
        }
        if (active != null) {
            return AssetBatchScheduleResult(assetPlan.objects.size, assetPlan.totalDownloadBytes, active.handle)
        }

        val handle = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            val jobId = stableJobId(request.progressPath)
            val jobHandle = "job:" + jobId
            DownloadProgressStore.enqueueAggregate(
                context, request.progressPath, plan.versionId + " · игровые ресурсы",
                request.totalBytes, jobHandle
            )
            val scheduler = context.getSystemService(Context.JOB_SCHEDULER_SERVICE) as JobScheduler
            val job = JobInfo.Builder(
                jobId,
                ComponentName(context, AssetBatchJobService::class.java)
            )
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                .setUserInitiated(true)
                .setEstimatedNetworkBytes(request.totalBytes, 0L)
                .setExtras(request.toBundle())
                .build()
            try {
                val result = scheduler.schedule(job)
                check(result == JobScheduler.RESULT_SUCCESS) {
                    "Android не принял пакетную загрузку ресурсов (код $result)"
                }
                jobHandle
            } catch (failure: Exception) {
                DownloadProgressStore.updateByHandle(
                    context, jobHandle, "FAILED",
                    failure.message ?: "Android отклонил пакетную загрузку"
                )
                throw failure
            }
        } else {
            val work = OneTimeWorkRequestBuilder<AssetBatchWorker>()
                .setInputData(request.toWorkData())
                .setConstraints(
                    Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build()
                )
                .addTag("nova-assets-" + AssetBatchManifest.sha256(request.versionId).take(20))
                .build()
            val workHandle = "work:" + work.id
            DownloadProgressStore.enqueueAggregate(
                context, request.progressPath, plan.versionId + " · игровые ресурсы",
                request.totalBytes, workHandle
            )
            try {
                WorkManager.getInstance(context).enqueueUniqueWork(
                    "nova-assets-" + AssetBatchManifest.sha256(request.versionId).take(20),
                    ExistingWorkPolicy.KEEP,
                    work
                )
                workHandle
            } catch (failure: Exception) {
                DownloadProgressStore.updateByHandle(
                    context, workHandle, "FAILED",
                    failure.message ?: "WorkManager отклонил пакетную загрузку"
                )
                throw failure
            }
        }

        return AssetBatchScheduleResult(
            assetObjects = assetPlan.objects.size,
            totalBytes = assetPlan.totalDownloadBytes,
            handle = handle
        )
    }

    private fun stableJobId(path: String): Int {
        val digest = MessageDigest.getInstance("SHA-256").digest(path.toByteArray(Charsets.UTF_8))
        val raw = ((digest[0].toInt() and 0xff) shl 24) or
            ((digest[1].toInt() and 0xff) shl 16) or
            ((digest[2].toInt() and 0xff) shl 8) or
            (digest[3].toInt() and 0xff)
        return 500_000 + (raw and 0x1fff_ffff)
    }
}

internal data class AssetBatchScheduleResult(
    val assetObjects: Int,
    val totalBytes: Long,
    val handle: String
)

internal class AssetBatchWorker(
    context: Context,
    parameters: WorkerParameters
) : CoroutineWorker(context, parameters) {
    override suspend fun doWork(): Result {
        val request = AssetBatchRequest.fromWorkData(inputData)
            ?: return Result.failure(workDataOf("error" to "Некорректный пакет ресурсов"))
        val notificationId = (id.hashCode() and 0x7fffffff).coerceAtLeast(1)
        val manager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE)
            as android.app.NotificationManager
        DownloadNotifications.ensureChannel(manager)

        return try {
            DownloadProgressStore.updateAggregate(
                applicationContext, request.progressPath,
                request.versionId + " · игровые ресурсы", "RUNNING", 0L, request.totalBytes
            )
            setForeground(foreground(notificationId, request, 0L, 0L))
            AssetBatchRunner.run(applicationContext, request) { downloaded, total, speed ->
                DownloadProgressStore.updateAggregate(
                    applicationContext, request.progressPath,
                    request.versionId + " · игровые ресурсы", "RUNNING", downloaded, total, speed
                )
                setProgress(workDataOf(
                    "downloaded" to downloaded,
                    "total" to total,
                    "bytes_per_second" to speed
                ))
                setForeground(foreground(notificationId, request, downloaded, speed))
            }
            DownloadProgressStore.updateAggregate(
                applicationContext, request.progressPath,
                request.versionId + " · игровые ресурсы", "COMPLETE",
                request.totalBytes, request.totalBytes
            )
            Result.success(workDataOf("objects" to request.objectCount, "bytes" to request.totalBytes))
        } catch (cancelled: CancellationException) {
            DownloadProgressStore.updateAggregate(
                applicationContext, request.progressPath,
                request.versionId + " · игровые ресурсы", "CANCELLED", 0L, request.totalBytes
            )
            throw cancelled
        } catch (failure: IOException) {
            val retrying = runAttemptCount < 4
            DownloadProgressStore.updateAggregate(
                applicationContext, request.progressPath,
                request.versionId + " · игровые ресурсы", if (retrying) "RETRYING" else "FAILED",
                0L, request.totalBytes, error = failure.message ?: "Ошибка загрузки"
            )
            if (retrying) Result.retry()
            else Result.failure(workDataOf("error" to (failure.message ?: "Ошибка загрузки")))
        } catch (failure: Exception) {
            DownloadProgressStore.updateAggregate(
                applicationContext, request.progressPath,
                request.versionId + " · игровые ресурсы", "FAILED", 0L, request.totalBytes,
                error = failure.message ?: "Ошибка ресурсов"
            )
            Result.failure(workDataOf("error" to (failure.message ?: "Ошибка ресурсов")))
        }
    }

    private fun foreground(
        notificationId: Int,
        request: AssetBatchRequest,
        downloaded: Long,
        speed: Long
    ): ForegroundInfo {
        val cancel = WorkManager.getInstance(applicationContext).createCancelPendingIntent(id)
        val notification = DownloadNotifications.build(
            applicationContext, request.versionId + " · игровые ресурсы",
            downloaded, request.totalBytes, speed, cancel
        )
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ForegroundInfo(
                notificationId, notification,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            )
        } else {
            ForegroundInfo(notificationId, notification)
        }
    }
}

internal class AssetBatchJobService : JobService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val activeJobs = ConcurrentHashMap<Int, Job>()

    override fun onStartJob(parameters: JobParameters): Boolean {
        val request = AssetBatchRequest.fromBundle(parameters.extras)
        if (request == null) {
            jobFinished(parameters, false)
            return false
        }

        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as android.app.NotificationManager
        DownloadNotifications.ensureChannel(manager)
        setNotification(
            parameters,
            parameters.jobId,
            notification(parameters.jobId, request, 0L, 0L),
            JOB_END_NOTIFICATION_POLICY_DETACH
        )
        DownloadProgressStore.updateAggregate(
            this, request.progressPath, request.versionId + " · игровые ресурсы",
            "RUNNING", 0L, request.totalBytes
        )

        val task = scope.launch {
            try {
                AssetBatchRunner.run(this@AssetBatchJobService, request) { downloaded, total, speed ->
                    DownloadProgressStore.updateAggregate(
                        this@AssetBatchJobService, request.progressPath,
                        request.versionId + " · игровые ресурсы", "RUNNING", downloaded, total, speed
                    )
                    withContext(Dispatchers.Main.immediate) {
                        setNotification(
                            parameters, parameters.jobId,
                            notification(parameters.jobId, request, downloaded, speed),
                            JOB_END_NOTIFICATION_POLICY_DETACH
                        )
                    }
                }
                DownloadProgressStore.updateAggregate(
                    this@AssetBatchJobService, request.progressPath,
                    request.versionId + " · игровые ресурсы", "COMPLETE",
                    request.totalBytes, request.totalBytes
                )
                manager.cancel(parameters.jobId)
                jobFinished(parameters, false)
            } catch (cancelled: CancellationException) {
                throw cancelled
            } catch (failure: Exception) {
                DownloadProgressStore.updateAggregate(
                    this@AssetBatchJobService, request.progressPath,
                    request.versionId + " · игровые ресурсы",
                    if (failure is IOException) "RETRYING" else "FAILED",
                    0L, request.totalBytes, error = failure.message ?: "Ошибка ресурсов"
                )
                manager.cancel(parameters.jobId)
                jobFinished(parameters, failure is IOException)
            } finally {
                activeJobs.remove(parameters.jobId)
            }
        }
        activeJobs[parameters.jobId] = task
        return true
    }

    private fun notification(jobId: Int, request: AssetBatchRequest, downloaded: Long, speed: Long): android.app.Notification {
        val intent = android.content.Intent(this, CancelArtifactJobReceiver::class.java)
            .putExtra(CancelArtifactJobReceiver.EXTRA_JOB_ID, jobId)
        val pending = android.app.PendingIntent.getBroadcast(
            this, jobId, intent,
            android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE
        )
        return DownloadNotifications.build(
            this, request.versionId + " · игровые ресурсы",
            downloaded, request.totalBytes, speed, pending
        )
    }

    override fun onStopJob(parameters: JobParameters): Boolean {
        activeJobs.remove(parameters.jobId)?.cancel()
        val handle = "job:" + parameters.jobId
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            (parameters.stopReason == JobParameters.STOP_REASON_USER ||
                parameters.stopReason == JobParameters.STOP_REASON_CANCELLED_BY_APP)
        ) {
            DownloadProgressStore.updateByHandle(this, handle, "CANCELLED")
            return false
        }
        DownloadProgressStore.updateByHandle(this, handle, "QUEUED")
        return true
    }

    override fun onDestroy() {
        scope.cancel()
        activeJobs.clear()
        super.onDestroy()
    }
}
