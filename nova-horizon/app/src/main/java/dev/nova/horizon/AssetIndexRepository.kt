package dev.nova.horizon

import java.io.File
import org.json.JSONObject

internal data class PlannedAssetObject(
    val hash: String,
    val size: Long,
    val url: String,
    val relativePath: String,
    val logicalKeys: List<String>
)

internal data class AssetIndexPlan(
    val assetIndexId: String,
    val objects: List<PlannedAssetObject>,
    val totalDownloadBytes: Long,
    val virtualAssets: Boolean,
    val mapToResources: Boolean
)

internal object AssetIndexRepository {
    private const val MAX_INDEX_BYTES = 32L * 1024L * 1024L

    fun parse(file: File, expectedId: String): AssetIndexPlan {
        require(expectedId.isNotBlank() && expectedId.length <= 64) {
            "Некорректный ID asset index"
        }
        if (!file.isFile || file.length() <= 0L || file.length() > MAX_INDEX_BYTES) {
            throw IllegalStateException("Asset index отсутствует или превышает допустимый размер")
        }

        val json = file.inputStream().buffered().use { input ->
            input.readBytes().toString(Charsets.UTF_8)
        }
        val result = JSONObject(NativeBridge.planAssetIndex(json, expectedId))
        if (result.has("ok") && !result.optBoolean("ok")) {
            throw SecurityException(
                "Rust Core отклонил asset index: " + result.optString("error", "неизвестная ошибка")
            )
        }
        val indexId = result.getString("assetIndexId")
        if (indexId != expectedId) {
            throw SecurityException("ID asset index не совпадает с выбранной версией")
        }

        val array = result.getJSONArray("objects")
        if (array.length() !in 1..150_000) {
            throw SecurityException("Количество asset objects вне допустимого диапазона")
        }

        val objects = ArrayList<PlannedAssetObject>(array.length())
        val seenHashes = HashSet<String>(array.length())
        var total = 0L

        for (index in 0 until array.length()) {
            val item = array.getJSONObject(index)
            val hash = item.getString("hash")
            val size = item.getLong("size")
            val url = item.getString("url")
            val path = item.getString("relativePath")
            val keysJson = item.getJSONArray("logicalKeys")
            val keys = ArrayList<String>(keysJson.length())
            for (keyIndex in 0 until keysJson.length()) {
                keys += keysJson.getString(keyIndex)
            }

            if (hash.length != 40 ||
                !hash.all { it in '0'..'9' || it.lowercaseChar() in 'a'..'f' } ||
                size <= 0L || keys.isEmpty() ||
                url != "https://resources.download.minecraft.net/" + hash.substring(0, 2) + "/" + hash ||
                path != "assets/objects/" + hash.substring(0, 2) + "/" + hash
            ) {
                throw SecurityException("Rust Core вернул некорректный asset object")
            }
            if (!seenHashes.add(hash)) {
                throw SecurityException("В плане повторяется SHA-1 asset object")
            }
            total = try {
                Math.addExact(total, size)
            } catch (_: ArithmeticException) {
                throw SecurityException("Суммарный размер asset objects переполнен")
            }
            objects += PlannedAssetObject(hash, size, url, path, keys)
        }

        val declaredTotal = result.getLong("totalDownloadBytes")
        if (total != declaredTotal) {
            throw SecurityException("Суммарный размер asset objects не совпадает с Rust-планом")
        }

        return AssetIndexPlan(
            assetIndexId = indexId,
            objects = objects,
            totalDownloadBytes = total,
            virtualAssets = result.optBoolean("virtualAssets", false),
            mapToResources = result.optBoolean("mapToResources", false)
        )
    }
}
