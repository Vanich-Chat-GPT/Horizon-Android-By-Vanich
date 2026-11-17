package dev.nova.horizon.account

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.nio.charset.StandardCharsets
import java.nio.file.AtomicMoveNotSupportedException
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.security.KeyStore
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

internal data class MinecraftSession(
    val accessToken: String,
    val expiresAtMillis: Long,
    val profileId: String,
    val profileName: String
) {
    fun isValid(nowMillis: Long = System.currentTimeMillis()): Boolean =
        accessToken.isNotBlank() && expiresAtMillis > nowMillis + 60_000L
}

/** Stores only the Minecraft token, encrypted with an Android Keystore AES-GCM key. */
internal object MinecraftSessionStore {
    private const val KEY_ALIAS = "dev.nova.horizon.minecraft-session.v1"
    private const val FILE_NAME = "minecraft-session.enc"
    private const val TRANSFORMATION = "AES/GCM/NoPadding"
    private const val TAG_BITS = 128

    fun save(context: Context, session: MinecraftSession) {
        require(session.accessToken.isNotBlank() && session.accessToken.length <= 16_384)
        require(session.profileId.matches(Regex("^[0-9a-fA-F-]{32,36}$")))
        require(session.profileName.isNotBlank() && session.profileName.length <= 64)
        require(session.expiresAtMillis > System.currentTimeMillis())

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val plain = JSONObject().apply {
            put("accessToken", session.accessToken)
            put("expiresAtMillis", session.expiresAtMillis)
            put("profileId", session.profileId)
            put("profileName", session.profileName)
        }.toString().toByteArray(StandardCharsets.UTF_8)
        val encrypted = cipher.doFinal(plain)
        val envelope = JSONObject().apply {
            put("version", 1)
            put("iv", Base64.getEncoder().encodeToString(cipher.iv))
            put("ciphertext", Base64.getEncoder().encodeToString(encrypted))
        }.toString().toByteArray(StandardCharsets.UTF_8)

        val directory = File(context.noBackupFilesDir, "nova-horizon").apply {
            if (!exists() && !mkdirs()) throw IllegalStateException("Не удалось создать защищённый каталог")
        }.canonicalFile
        val target = File(directory, FILE_NAME)
        val temporary = File(directory, FILE_NAME + ".tmp")
        FileOutputStream(temporary).use { output ->
            output.write(envelope)
            output.fd.sync()
        }
        try {
            Files.move(
                temporary.toPath(), target.toPath(),
                StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING
            )
        } catch (_: AtomicMoveNotSupportedException) {
            Files.move(
                temporary.toPath(), target.toPath(),
                StandardCopyOption.REPLACE_EXISTING
            )
        }
    }

    fun read(context: Context): MinecraftSession? {
        val file = File(context.noBackupFilesDir, "nova-horizon/$FILE_NAME")
        if (!file.isFile || file.length() !in 1..64_000L) return null

        return runCatching {
            val envelope = JSONObject(file.readText(StandardCharsets.UTF_8))
            require(envelope.getInt("version") == 1)
            val iv = Base64.getDecoder().decode(envelope.getString("iv"))
            val ciphertext = Base64.getDecoder().decode(envelope.getString("ciphertext"))
            require(iv.size == 12 && ciphertext.size in 17..32_768)

            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(
                Cipher.DECRYPT_MODE,
                getOrCreateKey(),
                GCMParameterSpec(TAG_BITS, iv)
            )
            val plain = JSONObject(String(cipher.doFinal(ciphertext), StandardCharsets.UTF_8))
            MinecraftSession(
                accessToken = plain.getString("accessToken"),
                expiresAtMillis = plain.getLong("expiresAtMillis"),
                profileId = plain.getString("profileId"),
                profileName = plain.getString("profileName")
            ).takeIf { it.isValid() }
        }.getOrNull()
    }

    fun clear(context: Context) {
        File(context.noBackupFilesDir, "nova-horizon/$FILE_NAME").delete()
    }

    private fun getOrCreateKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
    }
}
