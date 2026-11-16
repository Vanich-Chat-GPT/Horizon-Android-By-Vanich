use serde::Deserialize;
use serde_json::Value;

const MAX_METADATA_BYTES: usize = 16 * 1024 * 1024;
const CLIENT_HOSTS: &[&str] = &["piston-data.mojang.com", "launcher.mojang.com"];
const ASSET_INDEX_HOSTS: &[&str] = &["piston-meta.mojang.com", "piston-data.mojang.com"];
const LIBRARY_HOSTS: &[&str] = &["libraries.minecraft.net", "repo.maven.apache.org"];

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct VersionMetadata {
    pub id: String,
    #[serde(rename = "type")]
    pub version_type: String,
    pub main_class: String,
    pub java_version: Option<JavaRuntime>,
    pub asset_index: Option<AssetIndex>,
    pub downloads: Option<GameDownloads>,
    #[serde(default)]
    pub libraries: Vec<Library>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JavaRuntime {
    pub component: Option<String>,
    pub major_version: u32,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AssetIndex {
    pub id: String,
    pub sha1: String,
    pub size: u64,
    pub total_size: Option<u64>,
    pub url: String,
}

#[derive(Debug, Deserialize)]
pub struct GameDownloads {
    pub client: Option<DownloadArtifact>,
    #[serde(rename = "client_mappings")]
    pub client_mappings: Option<DownloadArtifact>,
}

#[derive(Debug, Deserialize)]
pub struct DownloadArtifact {
    pub sha1: String,
    pub size: u64,
    pub url: String,
    pub path: Option<String>,
    pub sha256: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct Library {
    pub name: String,
    pub url: Option<String>,
    pub downloads: Option<LibraryDownloads>,
    pub rules: Option<Vec<Value>>,
    pub natives: Option<Value>,
    pub extract: Option<Value>,
}

#[derive(Debug, Deserialize)]
pub struct LibraryDownloads {
    pub artifact: Option<DownloadArtifact>,
    pub classifiers: Option<std::collections::HashMap<String, DownloadArtifact>>,
}

#[derive(Debug, PartialEq, Eq)]
pub enum MetadataError {
    TooLarge,
    InvalidJson,
    InvalidVersionId,
    VersionIdMismatch,
    MissingMainClass,
    MissingAssetIndex,
    MissingClientDownload,
    InvalidJavaMajorVersion,
    InvalidLibraryName,
    UntrustedDownloadUrl,
    InvalidSha1,
    InvalidSha256,
    InvalidDownloadSize,
    InvalidRelativePath,
}

/// Parsed, validated subset of Mojang's version JSON.
///
/// This validates artifact identity and origin only. It intentionally does not resolve
/// OS/rule conditions or select native classifiers; Android must not download Linux
/// desktop natives and assume that they are Android-compatible.
impl VersionMetadata {
    pub fn parse(json: &str, expected_id: &str) -> Result<Self, MetadataError> {
        if json.len() > MAX_METADATA_BYTES {
            return Err(MetadataError::TooLarge);
        }

        let metadata: Self =
            serde_json::from_str(json).map_err(|_| MetadataError::InvalidJson)?;

        if !valid_id(&metadata.id) {
            return Err(MetadataError::InvalidVersionId);
        }
        if metadata.id != expected_id {
            return Err(MetadataError::VersionIdMismatch);
        }
        if metadata.main_class.trim().is_empty() {
            return Err(MetadataError::MissingMainClass);
        }
        if let Some(java) = &metadata.java_version {
            if !(8..=99).contains(&java.major_version) {
                return Err(MetadataError::InvalidJavaMajorVersion);
            }
        }

        let asset_index = metadata
            .asset_index
            .as_ref()
            .ok_or(MetadataError::MissingAssetIndex)?;
        if asset_index.id.trim().is_empty() {
            return Err(MetadataError::MissingAssetIndex);
        }
        validate_sha1(&asset_index.sha1)?;
        validate_size(asset_index.size)?;
        validate_url(&asset_index.url, ASSET_INDEX_HOSTS)?;

        let downloads = metadata
            .downloads
            .as_ref()
            .ok_or(MetadataError::MissingClientDownload)?;
        let client = downloads
            .client
            .as_ref()
            .ok_or(MetadataError::MissingClientDownload)?;
        validate_artifact(client, CLIENT_HOSTS)?;

        if let Some(mappings) = &downloads.client_mappings {
            validate_artifact(mappings, CLIENT_HOSTS)?;
        }

        for library in &metadata.libraries {
            if !valid_library_name(&library.name) {
                return Err(MetadataError::InvalidLibraryName);
            }

            if let Some(base_url) = &library.url {
                validate_url(base_url, LIBRARY_HOSTS)?;
            }
            if let Some(downloads) = &library.downloads {
                if let Some(artifact) = &downloads.artifact {
                    validate_artifact(artifact, LIBRARY_HOSTS)?;
                }
                if let Some(classifiers) = &downloads.classifiers {
                    for artifact in classifiers.values() {
                        validate_artifact(artifact, LIBRARY_HOSTS)?;
                    }
                }
            }
        }

        Ok(metadata)
    }

    pub fn client_download(&self) -> Option<&DownloadArtifact> {
        self.downloads.as_ref()?.client.as_ref()
    }

    pub fn library_count(&self) -> usize {
        self.libraries.len()
    }
}

fn valid_id(id: &str) -> bool {
    !id.is_empty()
        && id.len() <= 64
        && id.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-'))
}

fn valid_library_name(name: &str) -> bool {
    let mut parts = name.split(':');
    let group = parts.next().unwrap_or_default();
    let artifact = parts.next().unwrap_or_default();
    let version = parts.next().unwrap_or_default();
    let extra = parts.next();

    !group.is_empty()
        && !artifact.is_empty()
        && !version.is_empty()
        && extra.is_none()
        && [group, artifact, version].iter().all(|part| {
            part.bytes().all(|b| {
                b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-' | b'+')
            })
        })
}

fn validate_artifact(
    artifact: &DownloadArtifact,
    allowed_hosts: &[&str],
) -> Result<(), MetadataError> {
    validate_sha1(&artifact.sha1)?;
    validate_size(artifact.size)?;
    validate_url(&artifact.url, allowed_hosts)?;
    if let Some(sha256) = &artifact.sha256 {
        if sha256.len() != 64 || !sha256.bytes().all(|byte| byte.is_ascii_hexdigit()) {
            return Err(MetadataError::InvalidSha256);
        }
    }
    if let Some(path) = &artifact.path {
        if !valid_relative_path(path) {
            return Err(MetadataError::InvalidRelativePath);
        }
    }
    Ok(())
}

fn validate_sha1(value: &str) -> Result<(), MetadataError> {
    if value.len() != 40 || !value.bytes().all(|byte| byte.is_ascii_hexdigit()) {
        return Err(MetadataError::InvalidSha1);
    }
    Ok(())
}

fn validate_size(size: u64) -> Result<(), MetadataError> {
    if size == 0 {
        return Err(MetadataError::InvalidDownloadSize);
    }
    Ok(())
}

fn validate_url(url: &str, allowed_hosts: &[&str]) -> Result<(), MetadataError> {
    let safe_shape = !url.contains('@')
        && !url.contains('\\')
        && !url.contains('#')
        && !url.contains('?')
        && !url.bytes().any(|byte| byte.is_ascii_whitespace());

    let allowed = allowed_hosts.iter().any(|host| {
        let prefix = format!("https://{host}/");
        url.starts_with(&prefix)
    });

    if safe_shape && allowed {
        Ok(())
    } else {
        Err(MetadataError::UntrustedDownloadUrl)
    }
}

fn valid_relative_path(path: &str) -> bool {
    !path.is_empty()
        && !path.starts_with('/')
        && !path.contains('\\')
        && path
            .split('/')
            .all(|part| !part.is_empty() && part != "." && part != "..")
        && !path.bytes().any(|byte| byte.is_ascii_control())
}

#[cfg(test)]
mod tests {
    use super::{MetadataError, VersionMetadata};

    const VALID: &str = r#"{
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

    #[test]
    fn parses_valid_metadata_and_exposes_client_artifact() {
        let metadata = VersionMetadata::parse(VALID, "1.20.1").unwrap();
        assert_eq!(metadata.main_class, "net.minecraft.client.main.Main");
        assert_eq!(metadata.java_version.as_ref().unwrap().major_version, 17);
        assert_eq!(metadata.client_download().unwrap().size, 1000);
        assert_eq!(metadata.library_count(), 1);
    }

    #[test]
    fn rejects_metadata_for_another_version() {
        assert_eq!(
            VersionMetadata::parse(VALID, "1.20.2").unwrap_err(),
            MetadataError::VersionIdMismatch
        );
    }

    #[test]
    fn rejects_untrusted_client_url() {
        let hostile = VALID.replace(
            "https://piston-data.mojang.com/",
            "https://attacker.invalid/",
        );
        assert_eq!(
            VersionMetadata::parse(&hostile, "1.20.1").unwrap_err(),
            MetadataError::UntrustedDownloadUrl
        );
    }

    #[test]
    fn rejects_invalid_sha256() {
        let hostile = VALID.replace(
            "\"size\":1000,",
            "\"sha256\":\"not-a-hash\",\"size\":1000,",
        );
        assert_eq!(
            VersionMetadata::parse(&hostile, "1.20.1").unwrap_err(),
            MetadataError::InvalidSha256
        );
    }

    #[test]
    fn rejects_path_traversal() {
        let hostile = VALID.replace(
            "com/mojang/brigadier/1.1.8/brigadier-1.1.8.jar",
            "../outside.jar",
        );
        assert_eq!(
            VersionMetadata::parse(&hostile, "1.20.1").unwrap_err(),
            MetadataError::InvalidRelativePath
        );
    }
}
