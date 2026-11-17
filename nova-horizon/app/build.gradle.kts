plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val microsoftClientId = providers.gradleProperty("MICROSOFT_CLIENT_ID")
    .orElse(providers.environmentVariable("MICROSOFT_CLIENT_ID"))
    .orElse("")
    .get()
    .trim()
val microsoftRedirectHash = providers.gradleProperty("MICROSOFT_REDIRECT_SIGNATURE_HASH")
    .orElse(providers.environmentVariable("MICROSOFT_REDIRECT_SIGNATURE_HASH"))
    .orElse("")
    .get()
    .trim()
val authConfigured = microsoftClientId.isNotBlank() && microsoftRedirectHash.isNotBlank()
val msalResDirectory = layout.buildDirectory.dir("generated/msalConfig/res")
val releaseKeystorePath = providers.environmentVariable("ANDROID_KEYSTORE_PATH").orElse("").get()
val releaseStorePassword = providers.environmentVariable("ANDROID_KEYSTORE_PASSWORD").orElse("").get()
val releaseKeyAlias = providers.environmentVariable("ANDROID_KEY_ALIAS").orElse("").get()
val releaseKeyPassword = providers.environmentVariable("ANDROID_KEY_PASSWORD").orElse("").get()
val releaseSigningConfigured = releaseKeystorePath.isNotBlank() &&
    releaseStorePassword.isNotBlank() && releaseKeyAlias.isNotBlank() && releaseKeyPassword.isNotBlank()

android {
    namespace = "dev.nova.horizon"
    compileSdk = 36

    defaultConfig {
        applicationId = "dev.nova.horizon"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-dev"
        ndk {
            abiFilters += "arm64-v8a"
        }
        buildConfigField("String", "MICROSOFT_CLIENT_ID", "\"$microsoftClientId\"")
        buildConfigField("String", "MICROSOFT_REDIRECT_SIGNATURE_HASH", "\"$microsoftRedirectHash\"")
        buildConfigField("boolean", "MICROSOFT_AUTH_CONFIGURED", authConfigured.toString())
        manifestPlaceholders["msalSignatureHash"] = microsoftRedirectHash.ifBlank { "UNCONFIGURED" }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    sourceSets.getByName("main").res.srcDir(msalResDirectory)

    signingConfigs {
        create("release") {
            if (releaseSigningConfigured) {
                storeFile = file(releaseKeystorePath)
                storePassword = releaseStorePassword
                keyAlias = releaseKeyAlias
                keyPassword = releaseKeyPassword
            }
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            if (releaseSigningConfigured) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    packaging {
        jniLibs {
            useLegacyPackaging = false
        }
    }
}

val generateMsalConfig by tasks.registering {
    val output = msalResDirectory.map { it.file("raw/msal_config.json") }
    outputs.file(output)
    doLast {
        val file = output.get().asFile
        file.parentFile.mkdirs()
        val clientId = microsoftClientId.ifBlank { "00000000-0000-0000-0000-000000000000" }
        val signatureHash = microsoftRedirectHash.ifBlank { "UNCONFIGURED" }
        file.writeText(
            """
            {
              "client_id": "$clientId",
              "redirect_uri": "msauth://dev.nova.horizon/$signatureHash",
              "account_mode": "MULTIPLE",
              "authorities": [
                {
                  "type": "AAD",
                  "audience": {
                    "type": "AzureADandPersonalMicrosoftAccount",
                    "tenant_id": "consumers"
                  }
                }
              ]
            }
            """.trimIndent()
        )
    }
}

tasks.named("preBuild").configure {
    dependsOn(generateMsalConfig)
}

dependencies {
    implementation("com.microsoft.identity.client:msal:8.7.0")
    implementation(platform("androidx.compose:compose-bom:2025.08.00"))
    implementation("androidx.activity:activity-compose:1.10.1")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.work:work-runtime-ktx:2.12.0")
    debugImplementation("androidx.compose.ui:ui-tooling")
    testImplementation("junit:junit:4.13.2")
}
