import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

// Chave de assinatura, em keystore.properties na raiz do projeto android/.
// Não vai para o repositório. Sem ela o APK de release sai sem assinar.
val chave = Properties().apply {
    val f = rootProject.file("keystore.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

// O app é o mesmo index.html do site. Na hora de compilar ele é copiado
// para dentro do APK, então basta rodar o build para embarcar a versão atual.
val pastaDoApp = rootProject.projectDir.parentFile
val assetsGerados = layout.buildDirectory.dir("generated/speak-assets")
val copiarApp = tasks.register<Copy>("copiarApp") {
    from(pastaDoApp) { include("index.html") }
    into(assetsGerados)
}

android {
    namespace = "com.heliodados.speakja"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.heliodados.speakja"
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
    }

    signingConfigs {
        if (chave.isNotEmpty()) {
            create("speakja") {
                storeFile = file(chave.getProperty("storeFile"))
                storePassword = chave.getProperty("storePassword")
                keyAlias = chave.getProperty("keyAlias")
                keyPassword = chave.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            if (chave.isNotEmpty()) signingConfig = signingConfigs.getByName("speakja")
        }
    }

    sourceSets {
        getByName("main") {
            assets.srcDir(assetsGerados)
        }
    }

    // O lint da versão de release não roda no JDK 25 do Android Studio; não faz falta aqui.
    lint {
        checkReleaseBuilds = false
        abortOnError = false
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

tasks.named("preBuild") { dependsOn(copiarApp) }
