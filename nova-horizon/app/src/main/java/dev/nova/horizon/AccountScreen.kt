package dev.nova.horizon

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.height
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.nova.horizon.account.MinecraftAccountStore
import java.text.DateFormat
import java.util.Date

@Composable
internal fun AccountScreen() {
    val context = LocalContext.current
    val account = remember(context) { MinecraftAccountStore.read(context) }

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
                        else "Право на Java Edition не подтверждено",
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
                } else {
                    Text("Microsoft не подключён", fontWeight = FontWeight.Bold)
                    Text(
                        "Чтобы скачивать и запускать Minecraft Java Edition, лаунчер должен пройти вход Microsoft, обмен токенов Xbox Live/XSTS и проверку Minecraft Services entitlement.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        "Реальная авторизация будет включена после настройки собственного публичного Microsoft OAuth-приложения и redirect URI, совпадающего с подписью APK. Поддельный вход или ручная отметка о лицензии не используются.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
        Spacer(Modifier.height(4.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                "Загрузка игровых файлов заблокирована до подтверждения права на Java Edition.",
                color = MaterialTheme.colorScheme.error,
                fontWeight = FontWeight.Medium
            )
        }
    }
}
