package dev.nova.horizon

import android.app.Activity
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.nova.horizon.account.MinecraftAccountStore
import dev.nova.horizon.account.MinecraftAuthExchange
import dev.nova.horizon.account.MinecraftSessionStore
import dev.nova.horizon.account.MicrosoftAuthManager
import kotlinx.coroutines.launch
import java.text.DateFormat
import java.util.Date

@Composable
internal fun AccountScreen() {
    val context = LocalContext.current
    val activity = context as? Activity
    val scope = rememberCoroutineScope()
    var account by remember(context) { mutableStateOf(MinecraftAccountStore.read(context)) }
    var session by remember(context) { mutableStateOf(MinecraftSessionStore.read(context)) }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }

    fun updateOnUi(action: () -> Unit) {
        if (activity != null) activity.runOnUiThread(action) else action()
    }

    LaunchedEffect(account.isSignedIn, session?.expiresAtMillis) {
        if (account.isSignedIn &&
            (session == null || !session.isValid()) &&
            MicrosoftAuthManager.isConfigured()
        ) {
            busy = true
            MicrosoftAuthManager.initialize(context) { initialized ->
                initialized.fold(
                    onSuccess = {
                        MicrosoftAuthManager.acquireTokenSilently { tokenResult ->
                            tokenResult.fold(
                                onSuccess = { microsoftToken ->
                                    scope.launch {
                                        val result = runCatching {
                                            MinecraftAuthExchange.authenticate(context, microsoftToken)
                                        }
                                        busy = false
                                        result.onSuccess {
                                            account = MinecraftAccountStore.read(context)
                                            session = MinecraftSessionStore.read(context)
                                            message = "Сеанс Microsoft обновлён"
                                        }.onFailure {
                                            message = it.message ?: "Не удалось обновить сеанс Minecraft"
                                        }
                                    }
                                },
                                onFailure = { failure ->
                                    updateOnUi {
                                        busy = false
                                        message = "Автоматическое обновление не выполнено: " +
                                            (failure.message ?: "нужен повторный вход")
                                    }
                                }
                            )
                        }
                    },
                    onFailure = { failure ->
                        updateOnUi {
                            busy = false
                            message = failure.message ?: "Не удалось подготовить Microsoft OAuth"
                        }
                    }
                )
            }
        }
    }

    Column(
        Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Аккаунт", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
        ) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (account.isSignedIn) {
                    Text(account.profileName ?: "Minecraft account", fontWeight = FontWeight.Bold)
                    Text(
                        "Профиль: " + account.profileId,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        if (account.hasJavaEntitlement) "Право на Minecraft: Java Edition подтверждено"
                        else "Проверка права на Java Edition устарела — войдите снова",
                        color = if (account.hasJavaEntitlement) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.error
                        }
                    )
                    account.entitlementVerifiedAtMillis?.let {
                        Text(
                            "Проверено: " + DateFormat.getDateTimeInstance().format(Date(it)),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    session?.let {
                        Text(
                            if (it.isValid()) "Сеанс Minecraft действителен до " +
                                DateFormat.getDateTimeInstance().format(Date(it.expiresAtMillis))
                            else "Токен Minecraft истёк — требуется повторный вход",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                } else {
                    Text("Microsoft не подключён", fontWeight = FontWeight.Bold)
                    Text(
                        "Вход выполняется через системный браузер Microsoft. После него NOVA проверяет Xbox/XSTS, право на Java Edition и профиль Minecraft.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        if (!MicrosoftAuthManager.isConfigured()) {
            Text(
                "Авторизация подготовлена, но приложение Microsoft ещё не зарегистрировано для этой сборки. Для включения нужны MICROSOFT_CLIENT_ID и MICROSOFT_REDIRECT_SIGNATURE_HASH в настройках сборки/секретах GitHub. Клиентский секрет в APK не нужен и не должен добавляться.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodySmall
            )
        }

        Button(
            enabled = MicrosoftAuthManager.isConfigured() && activity != null && !busy,
            onClick = {
                busy = true
                message = "Подключение к Microsoft…"
                MicrosoftAuthManager.initialize(context) { initialized ->
                    initialized.onFailure { failure ->
                        updateOnUi {
                            busy = false
                            message = failure.message ?: "Не удалось подготовить Microsoft OAuth"
                        }
                    }
                    initialized.onSuccess {
                        if (activity == null) {
                            updateOnUi {
                                busy = false
                                message = "Не удалось получить Android Activity"
                            }
                        } else {
                            MicrosoftAuthManager.acquireToken(activity) { tokenResult ->
                                tokenResult.onFailure { failure ->
                                    updateOnUi {
                                        busy = false
                                        message = failure.message ?: "Вход Microsoft не выполнен"
                                    }
                                }
                                tokenResult.onSuccess { microsoftToken ->
                                    scope.launch {
                                        val result = runCatching {
                                            MinecraftAuthExchange.authenticate(context, microsoftToken)
                                        }
                                        busy = false
                                        result.onSuccess {
                                            account = MinecraftAccountStore.read(context)
                                            session = MinecraftSessionStore.read(context)
                                            message = "Аккаунт проверен: " + it.profileName
                                        }.onFailure {
                                            message = it.message ?: "Не удалось проверить аккаунт Minecraft"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(
                when {
                    busy -> "Подключение…"
                    account.isSignedIn -> "Обновить вход Microsoft"
                    else -> "Войти через Microsoft"
                }
            )
        }

        if (account.isSignedIn) {
            OutlinedButton(
                enabled = !busy,
                onClick = {
                    busy = true
                    MicrosoftAuthManager.signOut(context) { result ->
                        updateOnUi {
                            busy = false
                            result.onSuccess {
                                MinecraftSessionStore.clear(context)
                                MinecraftAccountStore.clear(context)
                                account = MinecraftAccountStore.read(context)
                                session = null
                                message = "Аккаунт отключён"
                            }.onFailure {
                                message = it.message ?: "Не удалось выйти из Microsoft"
                            }
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Выйти из аккаунта")
            }
        }

        message?.let {
            Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        Spacer(Modifier.height(4.dp))
        Text(
            "Скачивание игровых файлов разрешается только после положительного ответа Minecraft Services. Ошибки семейных/Xbox ограничений или отказа сервиса не обходятся.",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            style = MaterialTheme.typography.bodySmall
        )
    }
}
