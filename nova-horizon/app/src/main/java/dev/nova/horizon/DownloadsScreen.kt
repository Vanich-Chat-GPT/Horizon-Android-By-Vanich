package dev.nova.horizon

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import dev.nova.horizon.download.DownloadCoordinator
import dev.nova.horizon.download.DownloadHandle
import dev.nova.horizon.download.DownloadProgressEntry
import dev.nova.horizon.download.DownloadProgressStore
import kotlinx.coroutines.delay

@Composable
internal fun DownloadsScreen() {
    val context = LocalContext.current
    var entries by remember { mutableStateOf(emptyList<DownloadProgressEntry>()) }

    LaunchedEffect(context) {
        while (true) {
            entries = DownloadProgressStore.all(context)
            delay(750L)
        }
    }

    Column(
        Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("Загрузки", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Button(
                enabled = entries.any {
                    it.state == "COMPLETE" || it.state == "CANCELLED" || it.state == "FAILED"
                },
                onClick = {
                    DownloadProgressStore.clearFinished(context)
                    entries = DownloadProgressStore.all(context)
                }
            ) {
                Text("Очистить")
            }
        }

        Text(
            "Файлы сохраняются в приватный каталог приложения. Каждый файл проверяется по SHA-1 перед тем, как попасть в итоговую папку.",
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        if (entries.isEmpty()) {
            Spacer(Modifier.height(24.dp))
            Text("Пока нет заданий загрузки.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                items(entries, key = { it.path }) { entry ->
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surface
                        )
                    ) {
                        Column(
                            Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(7.dp)
                        ) {
                            Text(entry.displayName, fontWeight = FontWeight.SemiBold)
                            Text(
                                entry.path,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(statusLabel(entry.state), fontWeight = FontWeight.Medium)
                                Text(entry.percent.toString() + "%")
                            }
                            LinearProgressIndicator(
                                progress = { entry.percent / 100f },
                                modifier = Modifier.fillMaxWidth()
                            )
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    formatBytes(entry.downloadedBytes) + " / " + formatBytes(entry.totalBytes),
                                    style = MaterialTheme.typography.bodySmall
                                )
                                Text(
                                    if (entry.bytesPerSecond > 0L) {
                                        String.format(
                                            java.util.Locale.ROOT,
                                            "%.2f MB/s",
                                            entry.bytesPerSecond.toDouble() / (1024.0 * 1024.0)
                                        )
                                    } else {
                                        " "
                                    },
                                    style = MaterialTheme.typography.bodySmall
                                )
                            }
                            if (entry.error.isNotBlank()) {
                                Text(
                                    entry.error,
                                    color = MaterialTheme.colorScheme.error,
                                    style = MaterialTheme.typography.bodySmall
                                )
                            }
                            if (entry.state == "QUEUED" || entry.state == "RUNNING" || entry.state == "RETRYING") {
                                Button(
                                    onClick = {
                                        DownloadCoordinator.cancel(context, DownloadHandle(entry.handle))
                                        entries = DownloadProgressStore.all(context)
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text("Отменить загрузку")
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

private fun statusLabel(state: String): String = when (state) {
    "QUEUED" -> "В очереди"
    "RUNNING" -> "Загружается"
    "RETRYING" -> "Повторная попытка"
    "COMPLETE" -> "Проверен и сохранён"
    "FAILED" -> "Ошибка"
    "CANCELLED" -> "Отменено"
    else -> "Состояние: " + state
}

private fun formatBytes(bytes: Long): String {
    if (bytes < 1024L) return bytes.toString() + " B"
    if (bytes < 1024L * 1024L) {
        return String.format(java.util.Locale.ROOT, "%.1f KiB", bytes / 1024.0)
    }
    if (bytes < 1024L * 1024L * 1024L) {
        return String.format(java.util.Locale.ROOT, "%.1f MiB", bytes / (1024.0 * 1024.0))
    }
    return String.format(
        java.util.Locale.ROOT,
        "%.2f GiB",
        bytes / (1024.0 * 1024.0 * 1024.0)
    )
}
