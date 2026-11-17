package dev.nova.horizon.download

import android.content.Context
import dev.nova.horizon.account.MinecraftAccountStore
import kotlinx.coroutines.runBlocking

internal data class DownloadPlanScheduleResult(
    val totalArtifacts: Int,
    val newOrReusedTasks: Int,
    val totalBytes: Long
)

internal object DownloadPlanScheduler {
    fun enqueue(context: Context, plan: dev.nova.horizon.AndroidInstallPlan): DownloadPlanScheduleResult {
        val account = MinecraftAccountStore.read(context)
        check(account.hasJavaEntitlement) {
            "Сначала войдите в Microsoft и подтвердите право на Minecraft: Java Edition."
        }
        check(!plan.launchReady) {
            "План уже помечен как готовый; требуется повторная проверка runtime."
        }

        val artifacts = buildList {
            add(plan.client)
            addAll(plan.libraries)
        }.distinctBy { it.relativePath }

        require(artifacts.isNotEmpty()) { "План не содержит файлов для загрузки" }
        require(artifacts.size <= 80) {
            "Слишком много файлов для одной пакетной операции; разбейте установку на безопасные этапы."
        }

        val requests = artifacts.map { artifact ->
            OfficialArtifactRequest(
                url = artifact.url,
                sha1 = artifact.sha1,
                size = artifact.size,
                relativePath = artifact.relativePath,
                displayName = plan.versionId + " · " + artifact.kind
            ).also { it.validate() }
        }

        val indexRequest = OfficialArtifactRequest(
            url = plan.assetIndex.url,
            sha1 = plan.assetIndex.sha1,
            size = plan.assetIndex.size,
            relativePath = plan.assetIndex.relativePath,
            displayName = plan.versionId + " · asset index"
        ).also { it.validate() }
        DownloadStorageBudget.requireForArtifacts(context, requests + indexRequest)

        val assetBatch = runBlocking {
            AssetBatchCoordinator.prepareAndEnqueue(context, plan)
        }

        var scheduled = 0
        requests.forEach { request ->
            DownloadCoordinator.enqueue(context, request)
            scheduled += 1
        }

        val totalBytes = artifacts.fold(plan.assetIndex.size) { total, artifact ->
            total.saturatingAdd(artifact.size)
        }.saturatingAdd(assetBatch.totalBytes)
        return DownloadPlanScheduleResult(
            totalArtifacts = artifacts.size + 1 + assetBatch.assetObjects,
            newOrReusedTasks = scheduled + 1,
            totalBytes = totalBytes
        )
    }

    private fun Long.saturatingAdd(value: Long): Long =
        if (Long.MAX_VALUE - this < value) Long.MAX_VALUE else this + value
}
