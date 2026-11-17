package dev.nova.horizon

import android.app.ActivityManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import dev.nova.horizon.account.MinecraftAccountStore
import dev.nova.horizon.download.DownloadPlanScheduler
import java.util.concurrent.Executors

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { NovaApp() }
    }
}

private enum class NovaScreen(val title: String, val glyph: String) {
    HOME("Главная", "⌂"),
    VERSIONS("Версии", "▤"),
    DOWNLOADS("Загрузки", "↓"),
    ACCOUNT("Аккаунт", "♙"),
    SETTINGS("Настройки", "⚙"),
    DIAGNOSTICS("Диагностика", "⌁")
}

@Composable
private fun NovaApp() {
    val context = LocalContext.current
    val preferences = remember(context) {
        context.getSharedPreferences("nova_horizon_settings", Context.MODE_PRIVATE)
    }
    var selected by rememberSaveable { mutableStateOf(NovaScreen.HOME) }
    var darkTheme by remember {
        mutableStateOf(preferences.getBoolean("dark_theme", true))
    }

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
                    NovaScreen.DOWNLOADS -> DownloadsScreen()
                    NovaScreen.ACCOUNT -> AccountScreen()
                    NovaScreen.SETTINGS -> SettingsScreen(
                        darkTheme = darkTheme,
                        onThemeChanged = {
                            darkTheme = it
                            preferences.edit().putBoolean("dark_theme", it).apply()
                        }
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
                    StatusLine("Проба OpenGL ES", "Подключена")
                    StatusLine("Каталог версий", "Проверяется официально")
                    StatusLine("Загрузка игровых файлов", "Ещё не реализована")
                    StatusLine("Авторизация Microsoft", "Ещё не реализована")
                    StatusLine("Офлайн-запуск игры", "Ещё не реализован")
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
    var loadingCatalog by remember { mutableStateOf(false) }
    var catalog by remember { mutableStateOf<OfficialVersionCatalog?>(null) }
    var catalogError by remember { mutableStateOf<String?>(null) }
    var query by rememberSaveable { mutableStateOf("") }
    var inspectingId by remember { mutableStateOf<String?>(null) }
    var inspection by remember { mutableStateOf<VersionInspection?>(null) }
    var metadataError by remember { mutableStateOf<String?>(null) }
    var downloadMessage by remember { mutableStateOf<String?>(null) }
    var schedulingDownloads by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val account = remember(context) { MinecraftAccountStore.read(context) }

    val worker = remember {
        Executors.newSingleThreadExecutor { task ->
            Thread(task, "nova-version-metadata").apply { isDaemon = true }
        }
    }
    DisposableEffect(worker) {
        onDispose { worker.shutdownNow() }
    }

    val visibleVersions = remember(catalog, query) {
        val normalizedQuery = query.trim()
        catalog?.versions
            ?.filter { normalizedQuery.isEmpty() || it.id.contains(normalizedQuery, ignoreCase = true) }
            .orEmpty()
    }

    Column(
        Modifier.fillMaxSize().padding(22.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("Версии Minecraft", fontSize = 26.sp, fontWeight = FontWeight.Bold)
        Text(
            "Каталог берётся с официального сервера Mojang. Выбор версии проверяет её метаданные и формирует консервативный план установки для Android ARM64.",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontSize = 13.sp
        )
        Button(
            enabled = !loadingCatalog && inspectingId == null,
            onClick = {
                loadingCatalog = true
                catalogError = null
                inspection = null
                metadataError = null
                worker.execute {
                    val outcome = runCatching { VersionCatalogRepository.fetch() }
                    Handler(Looper.getMainLooper()).post {
                        loadingCatalog = false
                        outcome.onSuccess {
                            catalog = it
                            query = ""
                        }.onFailure {
                            catalogError = it.message ?: "Не удалось проверить каталог"
                        }
                    }
                }
            },
            modifier = Modifier.fillMaxWidth()
        ) {
            Text(if (loadingCatalog) "Получение официального каталога…" else "Обновить каталог версий")
        }

        if (loadingCatalog) {
            CircularProgressIndicator()
        }
        catalogError?.let {
            Text(it, color = MaterialTheme.colorScheme.error, fontSize = 13.sp)
        }

        catalog?.let { current ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text("Официальный каталог проверен", fontWeight = FontWeight.Bold)
                    StatusLine("Последний релиз", current.latestRelease)
                    StatusLine("Последний snapshot", current.latestSnapshot)
                    StatusLine("Всего версий", current.versionCount.toString())
                }
            }
        }

        OutlinedTextField(
            value = query,
            onValueChange = { query = it },
            enabled = catalog != null,
            singleLine = true,
            label = { Text("Поиск версии") },
            modifier = Modifier.fillMaxWidth()
        )

        inspection?.let { checked ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    val info = checked.metadata
                    val plan = checked.plan
                    Text("Метаданные и план проверены: " + info.id, fontWeight = FontWeight.Bold)
                    StatusLine("Тип", info.type)
                    StatusLine("Java", info.javaMajor?.toString() ?: "Не указан")
                    StatusLine("Главный класс", info.mainClass)
                    StatusLine("Asset index", info.assetIndexId ?: "Не указан")
                    StatusLine("Размер client JAR", info.clientSize?.let(::formatBytes) ?: "Не указан")
                    StatusLine("Библиотек в метаданных", info.libraryCount.toString())
                    Text("План установки Android ARM64", fontWeight = FontWeight.Bold)
                    StatusLine("Артефактов", plan.artifactCount.toString())
                    StatusLine("JAR-библиотек", plan.libraries.size.toString())
                    StatusLine("Размер известных файлов", formatBytes(plan.totalDownloadBytes))
                    StatusLine("Нерешённых требований", plan.issues.size.toString())
                    StatusLine("Можно запускать", if (plan.launchReady) "Да" else "Нет — runtime ещё не подключён")
                    Text(
                        "План включает client JAR, общие JAR-библиотеки и пакет ресурсов из официального asset index. Игровой запуск пока недоступен: Android Java runtime и графический мост ещё не подключены.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 12.sp
                    )
                    Button(
                        enabled = account.hasJavaEntitlement && !schedulingDownloads,
                        onClick = {
                            schedulingDownloads = true
                            downloadMessage = "Проверка asset index и подготовка пакетной загрузки…"
                            worker.execute {
                                val outcome = runCatching {
                                    DownloadPlanScheduler.enqueue(context, plan)
                                }
                                Handler(Looper.getMainLooper()).post {
                                    schedulingDownloads = false
                                    downloadMessage = outcome.fold(
                                        onSuccess = {
                                            "Подготовлено файлов: " + it.totalArtifacts +
                                                " · общий размер: " + formatBytes(it.totalBytes)
                                        },
                                        onFailure = { it.message ?: "Не удалось подготовить загрузку" }
                                    )
                                }
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (schedulingDownloads) "Подготовка загрузки…" else "Скачать игру и ресурсы")
                    }
                    if (!account.hasJavaEntitlement) {
                        Text(
                            "Для скачивания Minecraft сначала требуется подтверждённый вход Microsoft и право на Java Edition.",
                            color = MaterialTheme.colorScheme.error,
                            fontSize = 12.sp
                        )
                    }
                    downloadMessage?.let {
                        Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 12.sp)
                    }
                    plan.issues.take(8).forEach { issue ->
                        Text(
                            "• " + issue.library + ": " + issue.reason,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 11.sp
                        )
                    }
                }
            }
        }
        metadataError?.let {
            Text(it, color = MaterialTheme.colorScheme.error, fontSize = 13.sp)
        }

        LazyColumn(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(visibleVersions, key = { it.id }) { version ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(version.id, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                            Text(version.type, color = MaterialTheme.colorScheme.secondary, fontSize = 12.sp)
                        }
                        Text(
                            version.releaseTime,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 12.sp
                        )
                        Button(
                            enabled = inspectingId == null && !loadingCatalog,
                            onClick = {
                                inspectingId = version.id
                                inspection = null
                                metadataError = null
                                worker.execute {
                                    val outcome = runCatching {
                                        VersionCatalogRepository.inspectVersion(version)
                                    }
                                    Handler(Looper.getMainLooper()).post {
                                        inspectingId = null
                                        outcome.onSuccess { inspection = it }
                                            .onFailure {
                                                metadataError = it.message
                                                    ?: "Не удалось проверить метаданные версии"
                                            }
                                    }
                                }
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                if (inspectingId == version.id) "Проверка…" else "Проверить план установки"
                            )
                        }
                    }
                }
            }
        }
        if (catalog != null && visibleVersions.isEmpty()) {
            Text("Версии по этому запросу не найдены.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
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
                    "Редактор джойстика и кнопок будет реализован вместе с настоящим игровым input bridge.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun DiagnosticsScreen() {
    val context = LocalContext.current
    val coreStatus = remember { NativeBridge.status() }
    val hasVulkanFeature = remember {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.N &&
            context.packageManager.hasSystemFeature(PackageManager.FEATURE_VULKAN_HARDWARE_LEVEL)
    }
    val processorCount = remember { Runtime.getRuntime().availableProcessors() }
    val socModel = remember {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) Build.SOC_MODEL else Build.HARDWARE
    }
    val memory = remember {
        val manager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
        ActivityManager.MemoryInfo().also { manager.getMemoryInfo(it) }
    }
    val thermalStatus = remember {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val power = context.getSystemService(Context.POWER_SERVICE) as PowerManager
            power.currentThermalStatus.toString()
        } else {
            "API ниже 29"
        }
    }
    var glInfo by remember { mutableStateOf<GlProbeResult?>(null) }

    LazyColumn(
        Modifier.fillMaxSize().padding(22.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item { Text("Диагностика", fontSize = 26.sp, fontWeight = FontWeight.Bold) }
        item {
            AndroidView(
                factory = { viewContext ->
                    GlProbeView(viewContext) { result -> glInfo = result }
                },
                modifier = Modifier.fillMaxWidth().height(2.dp)
            )
        }
        item {
            Card(shape = RoundedCornerShape(20.dp)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Устройство", fontWeight = FontWeight.Bold)
                    StatusLine("Производитель", Build.MANUFACTURER)
                    StatusLine("Модель", Build.MODEL)
                    StatusLine("SoC / hardware", socModel.ifBlank { "Неизвестно" })
                    StatusLine("Android API", Build.VERSION.SDK_INT.toString())
                    StatusLine("Основная ABI", Build.SUPPORTED_ABIS.firstOrNull() ?: "Неизвестно")
                    StatusLine("Доступные ABI", Build.SUPPORTED_ABIS.joinToString())
                    StatusLine("CPU logical cores", processorCount.toString())
                    StatusLine("RAM всего", formatBytes(memory.totalMem))
                    StatusLine("RAM доступно сейчас", formatBytes(memory.availMem))
                    StatusLine("Thermal status", thermalStatus)
                }
            }
        }
        item {
            Card(shape = RoundedCornerShape(20.dp)) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Графический контекст", fontWeight = FontWeight.Bold)
                    StatusLine("GPU renderer", glInfo?.renderer ?: "Ожидание OpenGL ES…")
                    StatusLine("GL vendor", glInfo?.vendor ?: "Ожидание…")
                    StatusLine("OpenGL ES", glInfo?.version ?: "Ожидание…")
                    StatusLine("GLSL", glInfo?.shadingLanguage ?: "Ожидание…")
                    StatusLine("GL extensions", glInfo?.extensionCount?.toString() ?: "Ожидание…")
                    StatusLine(
                        "Vulkan feature",
                        if (hasVulkanFeature) "Объявлена Android; device ещё не проверен" else "Не объявлена"
                    )
                }
            }
        }
        item {
            Text("Rust Core", fontWeight = FontWeight.Bold)
            Text(coreStatus, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "GPU и GL-строки читаются из активного EGL-контекста. Vulkan пока только проверяется на наличие системной feature: создание Vulkan instance/device ещё не реализовано.",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 12.sp
            )
        }
    }
}

private fun formatBytes(value: Long): String {
    if (value <= 0L) return "Неизвестно"
    if (value < 1024L) return "$value B"
    if (value < 1024L * 1024L) {
        val kib = value.toDouble() / 1024.0
        return String.format(java.util.Locale.ROOT, "%.1f KiB", kib)
    }
    val mib = value.toDouble() / (1024.0 * 1024.0)
    return String.format(java.util.Locale.ROOT, "%.1f MiB", mib)
}
