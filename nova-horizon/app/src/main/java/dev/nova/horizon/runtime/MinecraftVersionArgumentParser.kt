package dev.nova.horizon.runtime

import org.json.JSONArray
import org.json.JSONObject

internal data class ParsedMinecraftArguments(
    val game: List<MinecraftArgumentEntry>,
    val jvm: List<MinecraftArgumentEntry>
)

/** Parses modern version JSON arguments and the legacy minecraftArguments string. */
internal object MinecraftVersionArgumentParser {
    fun parse(json: String): ParsedMinecraftArguments {
        require(json.toByteArray(Charsets.UTF_8).size <= 16 * 1024 * 1024) {
            "Метаданные версии Minecraft слишком велики"
        }
        val root = JSONObject(json)
        val arguments = root.optJSONObject("arguments")
        if (arguments != null) {
            return ParsedMinecraftArguments(
                game = parseEntries(arguments.optJSONArray("game") ?: JSONArray()),
                jvm = parseEntries(arguments.optJSONArray("jvm") ?: JSONArray())
            )
        }

        val legacy = root.optString("minecraftArguments", "")
        require(legacy.isNotBlank()) { "Версия не содержит поддерживаемых аргументов запуска" }
        return ParsedMinecraftArguments(
            game = listOf(MinecraftArgumentEntry(tokenizeLegacy(legacy))),
            jvm = emptyList()
        )
    }

    private fun parseEntries(array: JSONArray): List<MinecraftArgumentEntry> =
        (0 until array.length()).map { index ->
            when (val item = array.get(index)) {
                is String -> MinecraftArgumentEntry(listOf(item))
                is JSONObject -> {
                    val value = item.get("value")
                    val values = when (value) {
                        is String -> listOf(value)
                        is JSONArray -> (0 until value.length()).map { value.getString(it) }
                        else -> throw IllegalArgumentException("Некорректное значение аргумента Minecraft")
                    }
                    val rules = if (!item.has("rules")) {
                        null
                    } else {
                        val ruleArray = item.getJSONArray("rules")
                        (0 until ruleArray.length()).map { ruleIndex ->
                            parseRule(ruleArray.getJSONObject(ruleIndex))
                        }
                    }
                    MinecraftArgumentEntry(values, rules)
                }
                else -> throw IllegalArgumentException("Неизвестный формат аргумента Minecraft")
            }
        }

    private fun parseRule(value: JSONObject): MinecraftArgumentRule {
        val os = value.optJSONObject("os")
        val featuresObject = value.optJSONObject("features")
        val features = linkedMapOf<String, Boolean>()
        if (featuresObject != null) {
            val keys = featuresObject.keys()
            while (keys.hasNext()) {
                val key = keys.next()
                val featureValue = featuresObject.get(key)
                require(featureValue is Boolean) { "Некорректный feature-флаг Minecraft" }
                features[key] = featureValue
            }
        }
        return MinecraftArgumentRule(
            action = value.getString("action"),
            osName = os?.optString("name")?.takeIf { it.isNotBlank() },
            osArch = os?.optString("arch")?.takeIf { it.isNotBlank() },
            osVersionRegex = os?.optString("version")?.takeIf { it.isNotBlank() },
            features = features
        )
    }

    private fun tokenizeLegacy(value: String): List<String> {
        val result = mutableListOf<String>()
        val token = StringBuilder()
        var quote: Char? = null
        var escaping = false
        var tokenStarted = false
        value.forEach { char ->
            when {
                escaping -> {
                    token.append(char)
                    escaping = false
                    tokenStarted = true
                }
                char == '\\' && quote != null -> escaping = true
                quote != null && char == quote -> quote = null
                quote == null && (char == '"' || char == '\'') -> {
                    quote = char
                    tokenStarted = true
                }
                quote == null && char.isWhitespace() -> {
                    if (tokenStarted) {
                        result += token.toString()
                        token.setLength(0)
                        tokenStarted = false
                    }
                }
                else -> {
                    token.append(char)
                    tokenStarted = true
                }
            }
        }
        require(!escaping && quote == null) { "Незакрытая кавычка в аргументах Minecraft" }
        if (tokenStarted) result += token.toString()
        require(result.isNotEmpty()) { "Пустые аргументы запуска Minecraft" }
        return result
    }
}
