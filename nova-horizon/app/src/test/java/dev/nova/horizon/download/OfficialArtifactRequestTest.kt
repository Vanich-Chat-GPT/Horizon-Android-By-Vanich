package dev.nova.horizon.download

import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test

class OfficialArtifactRequestTest {
    private fun valid(
        url: String = "https://piston-data.mojang.com/v1/objects/abc/client.jar",
        sha1: String = "a".repeat(40),
        size: Long = 1024L,
        path: String = "versions/1.20.1/1.20.1.jar"
    ) = OfficialArtifactRequest(
        url = url,
        sha1 = sha1,
        size = size,
        relativePath = path,
        displayName = "Minecraft client"
    )

    @Test
    fun acceptsOfficialMojangAndLibraryHosts() {
        valid().validate()
        valid(
            url = "https://libraries.minecraft.net/com/mojang/example.jar",
            path = "libraries/com/mojang/example.jar"
        ).validate()
        valid(
            url = "https://repo.maven.apache.org/maven2/example/example.jar",
            path = "libraries/example/example.jar"
        ).validate()
        assertTrue(true)
    }

    @Test
    fun rejectsUnencryptedHttp() {
        assertThrows(IllegalArgumentException::class.java) {
            valid(url = "http://piston-data.mojang.com/client.jar").validate()
        }
    }

    @Test
    fun rejectsUntrustedHostAndHostSpoofing() {
        assertThrows(IllegalArgumentException::class.java) {
            valid(url = "https://example.invalid/client.jar").validate()
        }
        assertThrows(IllegalArgumentException::class.java) {
            valid(url = "https://piston-data.mojang.com.example.invalid/client.jar").validate()
        }
    }

    @Test
    fun rejectsUrlUserInfoQueryAndNonstandardPort() {
        assertThrows(IllegalArgumentException::class.java) {
            valid(url = "https://user@piston-data.mojang.com/client.jar").validate()
        }
        assertThrows(IllegalArgumentException::class.java) {
            valid(url = "https://piston-data.mojang.com/client.jar?redirect=https://evil.invalid").validate()
        }
        assertThrows(IllegalArgumentException::class.java) {
            valid(url = "https://piston-data.mojang.com:8443/client.jar").validate()
        }
    }

    @Test
    fun rejectsInvalidShaAndNonpositiveSize() {
        assertThrows(IllegalArgumentException::class.java) {
            valid(sha1 = "not-a-hash").validate()
        }
        assertThrows(IllegalArgumentException::class.java) {
            valid(size = 0L).validate()
        }
        assertThrows(IllegalArgumentException::class.java) {
            valid(size = -1L).validate()
        }
    }

    @Test
    fun rejectsPathTraversalAndAbsolutePaths() {
        assertThrows(IllegalArgumentException::class.java) {
            valid(path = "../outside.jar").validate()
        }
        assertThrows(IllegalArgumentException::class.java) {
            valid(path = "versions/../../outside.jar").validate()
        }
        assertThrows(IllegalArgumentException::class.java) {
            valid(path = "/absolute/outside.jar").validate()
        }
    }

    @Test
    fun rejectsBackslashAndControlCharactersInPaths() {
        assertThrows(IllegalArgumentException::class.java) {
            valid(path = "versions\\..\\outside.jar").validate()
        }
        assertThrows(IllegalArgumentException::class.java) {
            valid(path = "versions/1.20.1/\u0000client.jar").validate()
        }
    }
    @Test
    fun acceptsOnlyCompleteRemainingRangeWhenResuming() {
        OfficialArtifactDownloader.validateContentRange("bytes 512-1023/1024", 512L, 1024L)
    }

    @Test
    fun rejectsTruncatedOrMismatchedResumeRanges() {
        assertThrows(java.io.IOException::class.java) {
            OfficialArtifactDownloader.validateContentRange("bytes 512-900/1024", 512L, 1024L)
        }
        assertThrows(java.io.IOException::class.java) {
            OfficialArtifactDownloader.validateContentRange("bytes 511-1023/1024", 512L, 1024L)
        }
        assertThrows(java.io.IOException::class.java) {
            OfficialArtifactDownloader.validateContentRange("bytes 512-1023/2048", 512L, 1024L)
        }
        assertThrows(java.io.IOException::class.java) {
            OfficialArtifactDownloader.validateContentRange("bytes 0-1023/1024", 1024L, 1024L)
        }
    }

    @Test
    fun rejectsMalformedAndOverflowingResumeRanges() {
        assertThrows(java.io.IOException::class.java) {
            OfficialArtifactDownloader.validateContentRange("bytes nope-1023/1024", 512L, 1024L)
        }
        assertThrows(java.io.IOException::class.java) {
            OfficialArtifactDownloader.validateContentRange("bytes 512-9223372036854775808/1024", 512L, 1024L)
        }
    }

}
