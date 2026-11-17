package dev.nova.horizon.runtime

import java.io.File

/**
 * Converts the argument section of an official Minecraft version descriptor into
 * process arguments. This is deliberately independent of Android UI and JNI so it
 * can be tested on the host JVM.
 */
internal data class MinecraftArgumentRule(
    val action: String,
    val osName: String? = null,
    val osArch: String? = null,
    val osVersionRegex: String? = null,
    val features: Map<String, Boolean> = emptyMap()
)

internal data class MinecraftArgumentEntry(
    val values: List<String>,
    val rules: List<MinecraftArgumentRule>? = null
)

internal data class MinecraftLaunchEnvironment(
    val osName: String,
    val osArch: String,
    val osVersion: String,
    val features: Map<String, Boolean>
)

internal object MinecraftArgumentResolver {
    private val placeholder = Regex("\\$\\{([A-Za-z0-9_.-]+)}")

    fun resolve(
        entries: List<MinecraftArgumentEntry>,
        variables: Map<String, String>,
        environment: MinecraftLaunchEnvironment
    ): List<String> = buildList {
        entries.forEach { entry ->
            if (isAllowed(entry.rules, environment)) {
                entry.values.forEach { value ->
                    add(expand(value, variables))
                }
            }
        }
    }

    private fun isAllowed(
        rules: List<MinecraftArgumentRule>?,
        environment: MinecraftLaunchEnvironment
    ): Boolean {
        if (rules == null) return true
        var allowed = false
        rules.forEach { rule ->
            val matches = ruleMatches(rule, environment)
            if (matches) {
                allowed = when (rule.action) {
                    "allow" -> true
                    "disallow" -> false
                    else -> throw IllegalArgumentException("Неизвестное действие правила Minecraft")
                }
            } else if (rule.action != "allow" && rule.action != "disallow") {
                throw IllegalArgumentException("Неизвестное действие правила Minecraft")
            }
        }
        return allowed
    }

    private fun ruleMatches(
        rule: MinecraftArgumentRule,
        environment: MinecraftLaunchEnvironment
    ): Boolean {
        if (rule.osName != null && rule.osName != environment.osName) return false
        if (rule.osArch != null && !runCatching {
                Regex(rule.osArch).containsMatchIn(environment.osArch)
            }.getOrDefault(false)
        ) return false
        if (rule.osVersionRegex != null && !runCatching {
                Regex(rule.osVersionRegex).containsMatchIn(environment.osVersion)
            }.getOrDefault(false)
        ) return false
        return rule.features.all { (name, expected) ->
            environment.features[name] == expected
        }
    }

    private fun expand(value: String, variables: Map<String, String>): String {
        return placeholder.replace(value) { match ->
            variables[match.groupValues[1]]
                ?: throw IllegalArgumentException(
                    "Не задан параметр Minecraft: ${match.groupValues[1]}"
                )
        }
    }
}

/**
 * An already-resolved launch request. The command is an argv vector, never a shell
 * string: paths, player names and tokens cannot inject shell syntax.
 */
internal data class MinecraftLaunchSpec(
    val javaExecutable: File,
    val javaHome: File,
    val gameDirectory: File,
    val libraries: List<File>,
    val clientJar: File,
    val nativeDirectory: File,
    val temporaryDirectory: File,
    val mainClass: String,
    val jvmArguments: List<String>,
    val gameArguments: List<String>
) {
    fun command(): List<String> {
        require(javaExecutable.isFile) { "Java executable отсутствует" }
        require(javaHome.isDirectory) { "Java home отсутствует" }
        require(gameDirectory.isDirectory) { "Каталог игры отсутствует" }
        require(clientJar.isFile) { "Client JAR отсутствует" }
        require(nativeDirectory.isDirectory) { "Каталог native-библиотек отсутствует" }
        require(temporaryDirectory.isDirectory) { "Временный каталог отсутствует" }
        require(mainClass.matches(Regex("[A-Za-z0-9_.$]+"))) { "Некорректный mainClass" }
        require(libraries.isNotEmpty() && libraries.all { it.isFile }) {
            "Не все JAR-библиотеки установлены"
        }

        val classPath = (libraries + clientJar).joinToString(File.pathSeparator) { it.absolutePath }
        return buildList {
            add(javaExecutable.absolutePath)
            addAll(jvmArguments)
            // Android runtime paths are authoritative; version metadata must not override them.
            add("-Djava.home=${javaHome.absolutePath}")
            add("-Djava.io.tmpdir=${temporaryDirectory.absolutePath}")
            add("-Djava.library.path=${nativeDirectory.absolutePath}")
            add("-Dorg.lwjgl.librarypath=${nativeDirectory.absolutePath}")
            add("-cp")
            add(classPath)
            add(mainClass)
            addAll(gameArguments)
        }
    }
}


/** Starts the configured JVM without a shell and with the game directory as cwd. */
internal object MinecraftProcessRunner {
    fun start(spec: MinecraftLaunchSpec): Process =
        ProcessBuilder(spec.command())
            .directory(spec.gameDirectory)
            .redirectErrorStream(true)
            .start()
}
