package dev.nova.horizon.runtime

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class MinecraftLaunchArgumentsTest {
    private val androidArm64 = MinecraftLaunchEnvironment(
        osName = "android",
        osArch = "aarch64",
        osVersion = "16",
        features = mapOf(
            "has_custom_resolution" to true,
            "is_demo_user" to false
        )
    )

    @Test
    fun resolvesLiteralAndSubstitutedArgumentsWithoutSplittingValues() {
        val result = MinecraftArgumentResolver.resolve(
            listOf(
                MinecraftArgumentEntry(listOf("--username", "${'$'}{auth_player_name}")),
                MinecraftArgumentEntry(listOf("--width", "${'$'}{resolution_width}"))
            ),
            mapOf(
                "auth_player_name" to "Player With Spaces",
                "resolution_width" to "1280"
            ),
            androidArm64
        )

        assertEquals(
            listOf("--username", "Player With Spaces", "--width", "1280"),
            result
        )
    }

    @Test
    fun appliesOrderedAllowAndDisallowRules() {
        val entries = listOf(
            MinecraftArgumentEntry(
                listOf("-Dandroid=true"),
                listOf(MinecraftArgumentRule("allow", osName = "android"))
            ),
            MinecraftArgumentEntry(
                listOf("-Ddesktop=true"),
                listOf(MinecraftArgumentRule("allow", osName = "windows"))
            ),
            MinecraftArgumentEntry(
                listOf("-Ddisabled=true"),
                listOf(
                    MinecraftArgumentRule("allow"),
                    MinecraftArgumentRule("disallow", osName = "android")
                )
            )
        )

        assertEquals(listOf("-Dandroid=true"), MinecraftArgumentResolver.resolve(entries, emptyMap(), androidArm64))
    }

    @Test
    fun matchesArchitectureVersionRegexAndFeatureFlags() {
        val entries = listOf(
            MinecraftArgumentEntry(
                listOf("-Darm64=true"),
                listOf(MinecraftArgumentRule("allow", osArch = "aarch64|arm64"))
            ),
            MinecraftArgumentEntry(
                listOf("-Dapi16=true"),
                listOf(MinecraftArgumentRule("allow", osVersionRegex = "^1[5-9]"))
            ),
            MinecraftArgumentEntry(
                listOf("-Dresolution=true"),
                listOf(MinecraftArgumentRule("allow", features = mapOf("has_custom_resolution" to true)))
            ),
            MinecraftArgumentEntry(
                listOf("-Ddemo=true"),
                listOf(MinecraftArgumentRule("allow", features = mapOf("is_demo_user" to true)))
            )
        )

        assertEquals(
            listOf("-Darm64=true", "-Dapi16=true", "-Dresolution=true"),
            MinecraftArgumentResolver.resolve(entries, emptyMap(), androidArm64)
        )
    }

    @Test
    fun failsClosedForUnknownFeaturesAndUnknownPlaceholders() {
        val gated = MinecraftArgumentEntry(
            listOf("-Dunknown=true"),
            listOf(MinecraftArgumentRule("allow", features = mapOf("unknown_feature" to true)))
        )
        assertTrue(MinecraftArgumentResolver.resolve(listOf(gated), emptyMap(), androidArm64).isEmpty())

        assertThrows(IllegalArgumentException::class.java) {
            MinecraftArgumentResolver.resolve(
                listOf(MinecraftArgumentEntry(listOf("${'$'}{missing_token}"))),
                emptyMap(),
                androidArm64
            )
        }
    }

    @Test
    fun buildsArgumentVectorWithoutShellParsingOrImplicitRamCap() {
        val root = Files.createTempDirectory("nova-launch-test").toFile()
        try {
            val javaHome = File(root, "runtime").apply { mkdirs() }
            val java = File(javaHome, "bin-java").apply { writeText("test") }
            val game = File(root, "game").apply { mkdirs() }
            val natives = File(root, "natives").apply { mkdirs() }
            val temp = File(root, "tmp").apply { mkdirs() }
            val library = File(root, "library with spaces.jar").apply { writeText("jar") }

            val command = MinecraftLaunchSpec(
                javaExecutable = java,
                javaHome = javaHome,
                gameDirectory = game,
                libraries = listOf(library),
                clientJar = File(root, "client.jar").apply { writeText("client") },
                nativeDirectory = natives,
                temporaryDirectory = temp,
                mainClass = "net.minecraft.client.main.Main",
                jvmArguments = listOf("-Duser.language=ru"),
                gameArguments = listOf("--username", "Player;not-a-shell-command")
            ).command()

            assertEquals(java.absolutePath, command.first())
            assertTrue(command.contains(library.absolutePath))
            assertEquals("Player;not-a-shell-command", command.last())
            assertFalse(command.any { it.startsWith("-Xmx") })
            assertTrue(command.contains("net.minecraft.client.main.Main"))
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun rejectsMissingRuntimeFilesAndInvalidMainClass() {
        val root = Files.createTempDirectory("nova-launch-invalid").toFile()
        try {
            val folder = File(root, "dir").apply { mkdirs() }
            val java = File(root, "java").apply { writeText("test") }
            val library = File(root, "lib.jar").apply { writeText("jar") }
            val invalid = MinecraftLaunchSpec(
                javaExecutable = java,
                javaHome = folder,
                gameDirectory = folder,
                libraries = listOf(library),
                clientJar = File(root, "client.jar").apply { writeText("client") },
                nativeDirectory = folder,
                temporaryDirectory = folder,
                mainClass = "not a class",
                jvmArguments = emptyList(),
                gameArguments = emptyList()
            )
            assertThrows(IllegalArgumentException::class.java) { invalid.command() }
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun parsesModernGameAndJvmArgumentsFromVersionMetadata() {
        val metadata = """
            {
              "arguments": {
                "game": [
                  "--username",
                  {
                    "rules": [{"action":"allow","os":{"name":"android","arch":"aarch64"}}],
                    "value": ["\u0024{auth_player_name}", "--width", "\u0024{resolution_width}"]
                  },
                  {
                    "rules": [{"action":"allow","os":{"name":"windows"}}],
                    "value": "--quickPlayPath"
                  }
                ],
                "jvm": ["-Dfile.encoding=UTF-8"]
              }
            }
        """.trimIndent()

        val parsed = MinecraftVersionArgumentParser.parse(metadata)
        assertEquals(
            listOf("--username", "Steve", "--width", "1280"),
            MinecraftArgumentResolver.resolve(
                parsed.game,
                mapOf("auth_player_name" to "Steve", "resolution_width" to "1280"),
                androidArm64
            )
        )
        assertEquals(
            listOf("-Dfile.encoding=UTF-8"),
            MinecraftArgumentResolver.resolve(parsed.jvm, emptyMap(), androidArm64)
        )
    }

    @Test
    fun parsesLegacyMinecraftArgumentStringWithoutLosingQuotedValues() {
        val parsed = MinecraftVersionArgumentParser.parse(
            """{"minecraftArguments":"--username \"\u0024{auth_player_name}\" --server \"play.example:25565\""}"""
        )
        assertEquals(
            listOf("--username", "Player One", "--server", "play.example:25565"),
            MinecraftArgumentResolver.resolve(
                parsed.game,
                mapOf("auth_player_name" to "Player One"),
                androidArm64
            )
        )
    }

}
