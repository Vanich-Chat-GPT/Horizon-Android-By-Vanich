package dev.nova.horizon

import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { NovaApp() }
    }
}

private enum class NovaScreen(val title: String, val glyph: String) {
    HOME("Главная", "⌂"),
    VERSIONS("Версии", "▤"),
    SETTINGS("Настройки", "⚙"),
    DIAGNOSTICS("Диагностика", "⌁")
}

@Composable
private fun NovaApp() {
    var selected by rememberSaveable { mutableStateOf(NovaScreen.HOME) }
    var darkTheme by rememberSaveable { mutableStateOf(true) }

    val scheme = if (darkTheme) {
        darkColorScheme(
            primary = Color(0xFF9BB4FF),
            secondary = Color(0xFF75D6C4),
            background = Color(0xFF0B0E16),
            surface = Color(0xFF151B29)
        )
    } else {
        lightColorScheme(
            primary = Color(0xFF3458B8),
            secondary = Color(0xFF167B70)
        )
    }

    MaterialTheme(colorScheme = scheme) {
        Scaffold(
            bottomBar = {
                NavigationBar {
                    NovaScreen.entries.forEach { screen ->
                        NavigationBarItem(
                            selected = selected == screen,
                            onClick = { selected = screen },
                            icon = { Text(screen.glyph, fontSize = 19.sp) },
                            label = { Text(screen.title) }
                        )
                    }
                }
            }
        ) { padding ->
            Surface(
                modifier = Modifier.fillMaxSize().padding(padding),
                color = MaterialTheme.colorScheme.background
            ) {
                when (selected) {
                    NovaScreen.HOME -> HomeScreen(onDiagnostics = { selected = NovaScreen.DIAGNOSTICS })
                    NovaScreen.VERSIONS -> VersionsScreen()
                    NovaScreen.SETTINGS -> SettingsScreen(
                        darkTheme = darkTheme,
                        onThemeChanged = { darkTheme = it }
                    )
                    NovaScreen.DIAGNOSTICS -> DiagnosticsScreen()
                }
            }
        }
    }
}

@Composable
private fun HomeScreen(onDiagnostics: () -> Unit) {
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            Spacer(Modifier.height(12.dp))
            Text("NOVA", color = MaterialTheme.colorScheme.primary, fontSize = 13.sp, fontWeight = FontWeight.Bold)
            Text("HORIZON", fontSize = 34.sp, fontWeight = FontWeight.Black, letterSpacing = 1.5.sp)
            Text("Независимая Android-платформа", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(28.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("ИГРОВАЯ СРЕДА", color = MaterialTheme.colorScheme.secondary, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    Text("Пока не подключена", fontSize = 24.sp, fontWeight = FontWeight.Bold)
                    Text(
                        "JVM, графический мост и проверенный запуск Minecraft ещё находятся в разработке. Кнопка запуска появится только после реальной интеграции.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text("Версия NOVA: 0.1.0-dev", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("СОСТОЯНИЕ ПРОЕКТА", fontWeight = FontWeight.Bold)
                    StatusLine("Android оболочка", "Подготовлена")
                    StatusLine("Rust Core / JNI", "Подготовлен")
                    StatusLine("Загрузка Minecraft", "Не реализована")
                    StatusLine("Авторизация Microsoft", "Не реализована")
                    StatusLine("Офлайн-запуск игры", "Не реализован")
                }
            }
        }
        item {
            Button(onClick = onDiagnostics, modifier = Modifier.fillMaxWidth()) {
                Text("Открыть диагностику устройства")
            }
        }
        item {
            Text(
                "NOVA HORIZON — независимая разработка. Игровые файлы не входят в APK.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 12.sp,
                modifier = Modifier.padding(bottom = 20.dp)
            )
        }
    }
}

@Composable
private fun StatusLine(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun VersionsScreen() {
    Column(
        Modifier.fillMaxSize().padding(22.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Версии Minecraft", fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Text(
            "Каталог версий появится после реализации загрузчика официальных метаданных и проверки файлов. Сейчас список намеренно пуст — неподтверждённые версии не показываются.",
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun SettingsScreen(darkTheme: Boolean, onThemeChanged: (Boolean) -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(22.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        Text("Настройки", fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text("Тёмная тема", fontWeight = FontWeight.SemiBold)
                Text("Локальная настройка интерфейса", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
            }
            Switch(checked = darkTheme, onCheckedChange = onThemeChanged)
        }
        Card(shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Сенсорное управление", fontWeight = FontWeight.SemiBold)
                Text(
                    "Редактор джойстика и кнопок будет добавлен вместе с реальным игровым input bridge.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun DiagnosticsScreen() {
    val coreStatus = NativeBridge.status()
    Column(
        Modifier.fillMaxSize().padding(22.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Диагностика", fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Card(shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                StatusLine("Android API", Build.VERSION.SDK_INT.toString())
                StatusLine("Основная ABI", Build.SUPPORTED_ABIS.firstOrNull() ?: "Неизвестно")
                StatusLine("Доступные ABI", Build.SUPPORTED_ABIS.joinToString())
                StatusLine("GPU", "Проверка ещё не подключена")
                StatusLine("Vulkan", "Проверка ещё не подключена")
            }
        }
        Text("Rust Core", fontWeight = FontWeight.Bold)
        Text(coreStatus, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(
            "Данные GPU и реальные игровые метрики не подменяются предположениями по модели устройства.",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontSize = 12.sp
        )
    }
}
