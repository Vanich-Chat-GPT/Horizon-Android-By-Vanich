use crate::version_metadata::{DownloadArtifact, Library, VersionMetadata};
use serde::Serialize;
use serde_json::Value;

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct PlannedArtifact {
    pub kind: String,
    pub url: String,
    pub sha1: String,
    pub size: u64,
    pub relative_path: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct PlanIssue {
    pub library: String,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct AndroidInstallPlan {
    pub version_id: String,
    pub java_major_version: Option<u32>,
    pub client: PlannedArtifact,
    pub asset_index: PlannedArtifact,
    pub libraries: Vec<PlannedArtifact>,
    pub issues: Vec<PlanIssue>,
    pub total_download_bytes: u64,
    /// This remains false until a compatible JVM/native/rendering bridge exists.
    pub launch_ready: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InstallPlanError {
    InvalidVersionId,
    MissingClientArtifact,
    MissingAssetIndex,
    InvalidClientArtifact,
    InvalidAssetIndexArtifact,
}

/// Builds a conservative ARM64 Android install plan from metadata already validated by
/// VersionMetadata::parse. It never selects desktop native classifiers for Android.
pub fn build_android_install_plan(
    metadata: &VersionMetadata,
) -> Result<AndroidInstallPlan, InstallPlanError> {
    if !valid_relative_path(&format!("versions/{0}/{0}.jar", metadata.id)) || metadata.id.is_empty()
    {
        return Err(InstallPlanError::InvalidVersionId);
    }

    let client = metadata
        .client_download()
        .ok_or(InstallPlanError::MissingClientArtifact)?;
    let client_path = client
        .path
        .clone()
        .unwrap_or_else(|| format!("versions/{0}/{0}.jar", metadata.id));
    let client_artifact = planned_artifact(
        "client",
        client,
        client_path,
        InstallPlanError::InvalidClientArtifact,
    )?;

    let asset = metadata
        .asset_index
        .as_ref()
        .ok_or(InstallPlanError::MissingAssetIndex)?;
    let asset_artifact = PlannedArtifact {
        kind: "asset-index".to_owned(),
        url: asset.url.clone(),
        sha1: asset.sha1.to_ascii_lowercase(),
        size: asset.size,
        relative_path: format!("assets/indexes/{}.json", asset.id),
    };
    if !valid_relative_path(&asset_artifact.relative_path) {
        return Err(InstallPlanError::InvalidAssetIndexArtifact);
    }

    let mut libraries = Vec::new();
    let mut issues = Vec::new();
    for library in &metadata.libraries {
        let allowed = match android_rule_result(library) {
            Ok(allowed) => allowed,
            Err(reason) => {
                issues.push(PlanIssue {
                    library: library.name.clone(),
                    reason,
                });
                false
            }
        };

        if !allowed {
            if !issues.iter().any(|issue| issue.library == library.name) {
                issues.push(PlanIssue {
                    library: library.name.clone(),
                    reason: "Правила Mojang не разрешили эту библиотеку для профиля Android ARM64"
                        .to_owned(),
                });
            }
            continue;
        }

        if let Some(artifact) = library
            .downloads
            .as_ref()
            .and_then(|downloads| downloads.artifact.as_ref())
        {
            let path = artifact.path.clone().or_else(|| url_path(&artifact.url));
            match path {
                Some(path) if valid_relative_path(&path) => {
                    libraries.push(PlannedArtifact {
                        kind: "library".to_owned(),
                        url: artifact.url.clone(),
                        sha1: artifact.sha1.to_ascii_lowercase(),
                        size: artifact.size,
                        relative_path: path,
                    });
                }
                _ => issues.push(PlanIssue {
                    library: library.name.clone(),
                    reason: "Не удалось безопасно определить относительный путь JAR-файла"
                        .to_owned(),
                }),
            }
        } else {
            issues.push(PlanIssue {
                library: library.name.clone(),
                reason: "В метаданных отсутствует обычный artifact JAR".to_owned(),
            });
        }

        let has_classifiers = library
            .downloads
            .as_ref()
            .and_then(|downloads| downloads.classifiers.as_ref())
            .is_some_and(|classifiers| !classifiers.is_empty());

        if library.natives.is_some() || has_classifiers {
            issues.push(PlanIssue {
                library: library.name.clone(),
                reason: "Нативные classifiers не загружаются: Android/Bionic runtime bridge ещё не реализован".to_owned(),
            });
        }
    }

    let java_major_version = metadata
        .java_version
        .as_ref()
        .map(|runtime| runtime.major_version);

    let total_download_bytes = std::iter::once(client_artifact.size)
        .chain(std::iter::once(asset_artifact.size))
        .chain(libraries.iter().map(|artifact| artifact.size))
        .fold(0_u64, u64::saturating_add);

    Ok(AndroidInstallPlan {
        version_id: metadata.id.clone(),
        java_major_version,
        client: client_artifact,
        asset_index: asset_artifact,
        libraries,
        issues,
        total_download_bytes,
        launch_ready: false,
    })
}

fn planned_artifact(
    kind: &str,
    artifact: &DownloadArtifact,
    path: String,
    error: InstallPlanError,
) -> Result<PlannedArtifact, InstallPlanError> {
    if !valid_relative_path(&path) {
        return Err(error);
    }
    Ok(PlannedArtifact {
        kind: kind.to_owned(),
        url: artifact.url.clone(),
        sha1: artifact.sha1.to_ascii_lowercase(),
        size: artifact.size,
        relative_path: path,
    })
}

/// Mojang library rules are ordered: the last matching action wins.
/// Unknown conditions are treated as non-matching, never as permission to download.
fn android_rule_result(library: &Library) -> Result<bool, String> {
    let Some(rules) = library.rules.as_ref() else {
        return Ok(true);
    };

    let mut allowed = false;
    for rule in rules {
        let Some(object) = rule.as_object() else {
            return Err("Правило Mojang имеет неверную структуру".to_owned());
        };
        let action = object
            .get("action")
            .and_then(Value::as_str)
            .ok_or_else(|| "В правиле Mojang отсутствует action".to_owned())?;

        let matches = android_rule_matches(rule);
        if matches {
            match action {
                "allow" => allowed = true,
                "disallow" => allowed = false,
                _ => return Err("Неизвестное действие в правилах Mojang".to_owned()),
            }
        } else if action != "allow" && action != "disallow" {
            return Err("Неизвестное действие в правилах Mojang".to_owned());
        }
    }
    Ok(allowed)
}

fn android_rule_matches(rule: &Value) -> bool {
    let Some(object) = rule.as_object() else {
        return false;
    };

    for key in object.keys() {
        if key != "action" && key != "os" && key != "features" {
            return false;
        }
    }

    if let Some(os) = object.get("os") {
        let Some(os) = os.as_object() else {
            return false;
        };
        for (key, value) in os {
            match key.as_str() {
                "name" => {
                    if value.as_str() != Some("android") {
                        return false;
                    }
                }
                "arch" => {
                    if !matches!(value.as_str(), Some("aarch64" | "arm64" | "arm64-v8a")) {
                        return false;
                    }
                }
                // Android's exact release string is not supplied by this planner yet.
                "version" => return false,
                _ => return false,
            }
        }
    }

    if let Some(features) = object.get("features") {
        // Feature flags are not supplied to the planner, so no feature-gated rule can match.
        if !features.as_object().is_some_and(|values| values.is_empty()) {
            return false;
        }
    }

    true
}

fn valid_relative_path(path: &str) -> bool {
    !path.is_empty()
        && !path.starts_with('/')
        && !path.contains('\\')
        && !path.bytes().any(|byte| byte.is_ascii_control())
        && path
            .split('/')
            .all(|part| !part.is_empty() && part != "." && part != "..")
}

fn url_path(url: &str) -> Option<String> {
    let without_scheme = url.strip_prefix("https://")?;
    let slash = without_scheme.find('/')?;
    let path = without_scheme.get(slash + 1..)?;
    if path.is_empty() || path.contains('?') || path.contains('#') {
        return None;
    }
    Some(path.to_owned())
}

#[cfg(test)]
mod tests {
    use super::build_android_install_plan;
    use crate::version_metadata::VersionMetadata;

    const BASE: &str = r#"{
        "id":"1.20.1",
        "type":"release",
        "mainClass":"net.minecraft.client.main.Main",
        "javaVersion":{"component":"java-runtime-gamma","majorVersion":17},
        "assetIndex":{
            "id":"5",
            "sha1":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "size":100,
            "totalSize":100,
            "url":"https://piston-meta.mojang.com/v1/packages/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/5.json"
        },
        "downloads":{
            "client":{
                "sha1":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "size":1000,
                "url":"https://piston-data.mojang.com/v1/objects/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/client.jar"
            }
        },
        "libraries":[{
            "name":"com.mojang:brigadier:1.1.8",
            "downloads":{
                "artifact":{
                    "path":"com/mojang/brigadier/1.1.8/brigadier-1.1.8.jar",
                    "sha1":"cccccccccccccccccccccccccccccccccccccccc",
                    "size":200,
                    "url":"https://libraries.minecraft.net/com/mojang/brigadier/1.1.8/brigadier-1.1.8.jar"
                }
            }
        }]
    }"#;

    fn parse(value: &str) -> VersionMetadata {
        VersionMetadata::parse(value, "1.20.1").unwrap()
    }

    #[test]
    fn plan_contains_client_asset_index_and_generic_library() {
        let metadata = parse(BASE);
        let plan = build_android_install_plan(&metadata).unwrap();
        assert_eq!(plan.version_id, "1.20.1");
        assert_eq!(plan.java_major_version, Some(17));
        assert_eq!(plan.client.relative_path, "versions/1.20.1/1.20.1.jar");
        assert_eq!(plan.asset_index.relative_path, "assets/indexes/5.json");
        assert_eq!(plan.libraries.len(), 1);
        assert_eq!(plan.total_download_bytes, 1300);
        assert!(!plan.launch_ready);
    }

    #[test]
    fn excludes_linux_only_libraries() {
        let json = BASE.replace(
            "\"name\":\"com.mojang:brigadier:1.1.8\",",
            "\"name\":\"com.mojang:brigadier:1.1.8\",\"rules\":[{\"action\":\"allow\",\"os\":{\"name\":\"linux\"}}],"
        );
        let plan = build_android_install_plan(&parse(&json)).unwrap();
        assert!(plan.libraries.is_empty());
        assert_eq!(plan.issues.len(), 1);
    }

    #[test]
    fn includes_explicit_android_arm64_rule() {
        let json = BASE.replace(
            "\"name\":\"com.mojang:brigadier:1.1.8\",",
            "\"name\":\"com.mojang:brigadier:1.1.8\",\"rules\":[{\"action\":\"allow\",\"os\":{\"name\":\"android\",\"arch\":\"aarch64\"}}],"
        );
        let plan = build_android_install_plan(&parse(&json)).unwrap();
        assert_eq!(plan.libraries.len(), 1);
        assert!(plan.issues.is_empty());
    }

    #[test]
    fn reports_native_classifiers_instead_of_selecting_desktop_binary() {
        let json = BASE.replace(
            "\"name\":\"com.mojang:brigadier:1.1.8\",",
            "\"name\":\"com.mojang:brigadier:1.1.8\",\"natives\":{\"linux\":\"natives-linux\"},",
        );
        let plan = build_android_install_plan(&parse(&json)).unwrap();
        assert_eq!(plan.libraries.len(), 1);
        assert_eq!(plan.issues.len(), 1);
        assert!(plan.issues[0].reason.contains("Android/Bionic"));
    }

    #[test]
    fn unknown_feature_rules_are_conservatively_excluded() {
        let json = BASE.replace(
            "\"name\":\"com.mojang:brigadier:1.1.8\",",
            "\"name\":\"com.mojang:brigadier:1.1.8\",\"rules\":[{\"action\":\"allow\",\"features\":{\"has_custom_resolution\":true}}],"
        );
        let plan = build_android_install_plan(&parse(&json)).unwrap();
        assert!(plan.libraries.is_empty());
        assert_eq!(plan.issues.len(), 1);
    }
}
