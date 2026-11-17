package dev.nova.horizon.account

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.URI
import java.net.URL
import java.nio.charset.StandardCharsets
import javax.net.ssl.HttpsURLConnection

internal data class MinecraftAuthenticationResult(
    val profileId: String,
    val profileName: String,
    val expiresAtMillis: Long
)

/**
 * Exchanges a Microsoft access token for Xbox Live, XSTS and Minecraft Services tokens.
 * The Microsoft token must come from the registered public-client OAuth flow (MSAL).
 * Tokens are never written to logs or ordinary preferences.
 */
internal object MinecraftAuthExchange {
    private const val MAX_RESPONSE_BYTES = 1024 * 1024
    private const val CONNECT_TIMEOUT_MS = 12_000
    private const val READ_TIMEOUT_MS = 20_000

    suspend fun authenticate(
        context: Context,
        microsoftAccessToken: String
    ): MinecraftAuthenticationResult = withContext(Dispatchers.IO) {
        require(microsoftAccessToken.isNotBlank() && microsoftAccessToken.length <= 32_768)

        val xbox = postJson(
            "https://user.auth.xboxlive.com/user/authenticate",
            JSONObject().apply {
                put("Properties", JSONObject().apply {
                    put("AuthMethod", "RPS")
                    put("SiteName", "user.auth.xboxlive.com")
                    put("RpsTicket", "d=" + microsoftAccessToken)
                })
                put("RelyingParty", "http://auth.xboxlive.com")
                put("TokenType", "JWT")
            }
        )
        val xboxToken = xbox.getString("Token")
        val userHash = xbox.getJSONObject("DisplayClaims")
            .getJSONArray("xui")
            .getJSONObject(0)
            .getString("uhs")

        val xsts = postJson(
            "https://xsts.auth.xboxlive.com/xsts/authorize",
            JSONObject().apply {
                put("Properties", JSONObject().apply {
                    put("SandboxId", "RETAIL")
                    put("UserTokens", JSONArray().put(xboxToken))
                })
                put("RelyingParty", "rp://api.minecraftservices.com/")
                put("TokenType", "JWT")
            }
        )
        val xstsToken = xsts.getString("Token")
        val identityToken = "XBL3.0 x=" + userHash + ";" + xstsToken

        val minecraft = postJson(
            "https://api.minecraftservices.com/authentication/login_with_xbox",
            JSONObject().put("identityToken", identityToken)
        )
        val minecraftToken = minecraft.getString("access_token")
        val expiresIn = minecraft.optLong("expires_in", 0L)
        require(minecraftToken.isNotBlank() && expiresIn in 60L..604_800L) {
            "Minecraft Services вернул некорректный срок действия токена"
        }

        val entitlement = getJson(
            "https://api.minecraftservices.com/entitlements/mcstore",
            minecraftToken
        )
        val items = entitlement.optJSONArray("items") ?: JSONArray()
        val ownsJava = (0 until items.length()).any { index ->
            val name = items.optJSONObject(index)?.optString("name").orEmpty()
            name == "product_minecraft" || name == "game_minecraft"
        }
        check(ownsJava) {
            "Minecraft Services не подтвердил право на Minecraft: Java Edition для этого аккаунта."
        }

        val profile = getJson(
            "https://api.minecraftservices.com/minecraft/profile",
            minecraftToken
        )
        val profileId = profile.getString("id")
        val profileName = profile.getString("name")
        val expiresAt = System.currentTimeMillis() + expiresIn * 1000L

        MinecraftSessionStore.save(
            context,
            MinecraftSession(minecraftToken, expiresAt, profileId, profileName)
        )
        MinecraftAccountStore.saveVerifiedProfile(
            context, profileId, profileName, System.currentTimeMillis()
        )

        MinecraftAuthenticationResult(profileId, profileName, expiresAt)
    }

    private fun postJson(address: String, payload: JSONObject): JSONObject {
        val url = URL(address)
        validateHost(
            url,
            setOf("user.auth.xboxlive.com", "xsts.auth.xboxlive.com", "api.minecraftservices.com")
        )
        val connection = url.openConnection() as HttpsURLConnection
        connection.connectTimeout = CONNECT_TIMEOUT_MS
        connection.readTimeout = READ_TIMEOUT_MS
        connection.requestMethod = "POST"
        connection.instanceFollowRedirects = false
        connection.doOutput = true
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        connection.setRequestProperty("User-Agent", "NOVA-HORIZON/0.1.0-dev (Android)")
        return try {
            connection.outputStream.use { output ->
                output.write(payload.toString().toByteArray(StandardCharsets.UTF_8))
            }
            readResponse(connection)
        } finally {
            connection.disconnect()
        }
    }

    private fun getJson(address: String, bearerToken: String): JSONObject {
        val url = URL(address)
        validateHost(url, setOf("api.minecraftservices.com"))
        val connection = url.openConnection() as HttpsURLConnection
        connection.connectTimeout = CONNECT_TIMEOUT_MS
        connection.readTimeout = READ_TIMEOUT_MS
        connection.requestMethod = "GET"
        connection.instanceFollowRedirects = false
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("Authorization", "Bearer " + bearerToken)
        connection.setRequestProperty("User-Agent", "NOVA-HORIZON/0.1.0-dev (Android)")
        return try {
            readResponse(connection)
        } finally {
            connection.disconnect()
        }
    }

    private fun readResponse(connection: HttpsURLConnection): JSONObject {
        val status = connection.responseCode
        val stream = if (status in 200..299) connection.inputStream else connection.errorStream
        val body = stream?.use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(16 * 1024)
            var total = 0
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                total += read
                if (total > MAX_RESPONSE_BYTES) {
                    throw IOException("Ответ службы авторизации слишком большой")
                }
                output.write(buffer, 0, read)
            }
            output.toByteArray()
        } ?: ByteArray(0)

        if (status !in 200..299) {
            val code = runCatching {
                JSONObject(String(body, StandardCharsets.UTF_8)).optString("XErr")
            }.getOrDefault("")
            val suffix = if (code.isNotBlank()) ", код " + code else ""
            throw IOException(
                when (status) {
                    401 -> "Служба авторизации отклонила токен (HTTP 401" + suffix + ")."
                    403 -> "Служба авторизации запретила запрос (HTTP 403). Проверьте доступ Microsoft/Xbox и разрешение приложения."
                    else -> "Служба авторизации вернула HTTP " + status + "."
                }
            )
        }
        if (body.isEmpty()) throw IOException("Служба авторизации вернула пустой ответ")
        return JSONObject(String(body, StandardCharsets.UTF_8))
    }

    private fun validateHost(url: URL, allowed: Set<String>) {
        val uri = URI(url.toString())
        if (!uri.scheme.equals("https", ignoreCase = true) ||
            uri.host?.lowercase() !in allowed ||
            uri.userInfo != null ||
            uri.rawFragment != null ||
            (uri.port != -1 && uri.port != 443)
        ) {
            throw SecurityException("Заблокирован недоверенный адрес авторизации")
        }
    }
}
