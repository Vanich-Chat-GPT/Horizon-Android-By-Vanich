package dev.nova.horizon.download

import android.app.Notification
import android.app.PendingIntent
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.job.JobParameters
import android.app.job.JobService
import android.app.job.JobScheduler
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.content.pm.ServiceInfo
import androidx.core.app.NotificationCompat
import androidx.work.CoroutineWorker
import androidx.work.ForegroundInfo
import androidx.work.WorkerParameters
import androidx.work.WorkManager
import androidx.work.workDataOf
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.IOException
import java.util.concurrent.ConcurrentHashMap

internal object DownloadNotifications {
    const val CHANNEL_ID = "nova_downloads"

    fun build(context: Context, title: String, downloaded: Long, total: Long, speed: Long, cancelIntent: PendingIntent? = null): Notification {
        val percent = if (total > 0L) ((downloaded * 100L) / total).toInt().coerceIn(0, 100) else 0
        val speedText = if (speed > 0L) {
            String.format(java.util.Locale.ROOT, "%.2f MB/s", speed.toDouble() / (1024.0 * 1024.0))
        } else {
            "Подготовка…"
        }
        val builder = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setContentTitle(title.ifBlank { "NOVA HORIZON" })
            .setContentText(speedText + " · " + percent + "%")
            .setProgress(100, percent, false)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setCategory(NotificationCompat.CATEGORY_PROGRESS)
        if (cancelIntent != null) {
            builder.addAction(
                android.R.drawable.ic_menu_close_clear_cancel,
                "Отменить",
                cancelIntent
            )
        }
        return builder.build()
    }

    fun ensureChannel(manager: NotificationManager) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Загрузки NOVA HORIZON", NotificationManager.IMPORTANCE_LOW)
            )
        }
    }

}

/** WorkManager fallback for Android 8–13; API 34+ uses a user-initiated data transfer job. */
internal class OfficialArtifactDownloadWorker(
    context: Context,
    parameters: WorkerParameters
) : CoroutineWorker(context, parameters) {

    override suspend fun doWork(): Result {
        val request = OfficialArtifactRequest.fromWorkData(inputData)
            ?: return Result.failure(workDataOf("error" to "Некорректное задание загрузки"))
        val notificationId = (id.hashCode() and 0x7fffffff).coerceAtLeast(1)
        val manager = applicationContext.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        DownloadNotifications.ensureChannel(manager)

        return try {
            setForeground(foreground(notificationId, request.displayName, 0L, request.size, 0L))
            val result = OfficialArtifactDownloader.download(applicationContext, request) { downloaded, total, speed ->
                setProgress(
                    workDataOf(
                        "downloaded" to downloaded,
                        "total" to total,
                        "bytes_per_second" to speed
                    )
                )
                setForeground(foreground(notificationId, request.displayName, downloaded, total, speed))
            }
            Result.success(
                workDataOf(
                    "path" to result.file.absolutePath,
                    "downloaded" to result.downloadedBytes,
                    "already_present" to result.alreadyPresent
                )
            )
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (io: IOException) {
            if (runAttemptCount < 4) Result.retry()
            else Result.failure(workDataOf("error" to (io.message ?: "Ошибка сети/хранилища")))
        } catch (failure: Exception) {
            Result.failure(workDataOf("error" to (failure.message ?: "Ошибка проверки файла")))
        }
    }

    private fun foreground(
        notificationId: Int,
        title: String,
        downloaded: Long,
        total: Long,
        speed: Long
    ): ForegroundInfo {
        val cancelIntent = WorkManager.getInstance(applicationContext).createCancelPendingIntent(this.id)
        val notification = DownloadNotifications.build(
            applicationContext, title, downloaded, total, speed, cancelIntent
        )
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ForegroundInfo(notificationId, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC)
        } else {
            ForegroundInfo(notificationId, notification)
        }
    }
}

/** Android 14+ service used only for explicit, user-started large transfers. */
internal class ArtifactDownloadJobService : JobService() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val activeJobs = ConcurrentHashMap<Int, Job>()

    override fun onStartJob(parameters: JobParameters): Boolean {
        val request = OfficialArtifactRequest.fromPersistableBundle(parameters.extras)
        if (request == null) {
            jobFinished(parameters, false)
            return false
        }

        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        DownloadNotifications.ensureChannel(manager)
        setNotification(
            parameters,
            parameters.jobId,
            buildJobNotification(parameters.jobId, request.displayName, 0L, request.size, 0L),
            JOB_END_NOTIFICATION_POLICY_DETACH
        )

        val task = scope.launch {
            try {
                OfficialArtifactDownloader.download(this@ArtifactDownloadJobService, request) { downloaded, total, speed ->
                    withContext(Dispatchers.Main.immediate) {
                        setNotification(
                            parameters,
                            parameters.jobId,
                            buildJobNotification(
                                parameters.jobId, request.displayName, downloaded, total, speed
                            ),
                            JOB_END_NOTIFICATION_POLICY_DETACH
                        )
                    }
                }
                manager.cancel(parameters.jobId)
                jobFinished(parameters, false)
            } catch (cancelled: CancellationException) {
                // onStopJob owns the rescheduling decision.
                throw cancelled
            } catch (failure: Exception) {
                manager.cancel(parameters.jobId)
                jobFinished(parameters, failure is IOException)
            } finally {
                activeJobs.remove(parameters.jobId)
            }
        }
        activeJobs[parameters.jobId] = task
        return true
    }

    private fun buildJobNotification(
        jobId: Int,
        title: String,
        downloaded: Long,
        total: Long,
        speed: Long
    ): Notification {
        val intent = Intent(this, CancelArtifactJobReceiver::class.java)
            .putExtra(CancelArtifactJobReceiver.EXTRA_JOB_ID, jobId)
        val pendingIntent = PendingIntent.getBroadcast(
            this,
            jobId,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return DownloadNotifications.build(this, title, downloaded, total, speed, pendingIntent)
    }

    override fun onStopJob(parameters: JobParameters): Boolean {
        activeJobs.remove(parameters.jobId)?.cancel()
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            parameters.stopReason != JobParameters.STOP_REASON_USER &&
                parameters.stopReason != JobParameters.STOP_REASON_CANCELLED_BY_APP
        } else {
            true
        }
    }

    override fun onDestroy() {
        scope.cancel()
        activeJobs.clear()
        super.onDestroy()
    }
}

internal class CancelArtifactJobReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val jobId = intent.getIntExtra(EXTRA_JOB_ID, -1)
        if (jobId > 0) {
            (context.getSystemService(Context.JOB_SCHEDULER_SERVICE) as JobScheduler).cancel(jobId)
        }
    }

    companion object {
        const val EXTRA_JOB_ID = "job_id"
    }
}
