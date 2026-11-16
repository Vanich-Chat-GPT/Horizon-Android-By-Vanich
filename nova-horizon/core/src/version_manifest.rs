use serde::{Deserialize, Serialize};
use std::collections::HashSet;

const OFFICIAL_METADATA_PREFIX: &str = "https://piston-meta.mojang.com/";

#[derive(Debug, Deserialize, Serialize)]
pub struct VersionManifest {
    pub latest: LatestVersions,
    pub versions: Vec<VersionEntry>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct LatestVersions {
    pub release: String,
    pub snapshot: String,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct VersionEntry {
    pub id: String,
    #[serde(rename = "type")]
    pub version_type: String,
    pub url: String,
    #[serde(rename = "releaseTime")]
    pub release_time: String,
    pub sha1: String,
    #[serde(rename = "complianceLevel")]
    pub compliance_level: Option<u8>,
}

#[derive(Debug, PartialEq, Eq)]
pub enum ManifestError {
    InvalidJson,
    EmptyVersions,
    InvalidVersionId,
    DuplicateVersionId,
    UntrustedMetadataUrl,
    InvalidSha1,
    LatestVersionMissing,
}

impl VersionManifest {
    /// Parse and validate the public Mojang Java version manifest.
    /// This function does not download game files or authorize an account.
    pub fn parse(json: &str) -> Result<Self, ManifestError> {
        let manifest: Self = serde_json::from_str(json).map_err(|_| ManifestError::InvalidJson)?;

        if manifest.versions.is_empty() {
            return Err(ManifestError::EmptyVersions);
        }

        let mut ids = HashSet::with_capacity(manifest.versions.len());
        for version in &manifest.versions {
            if version.id.is_empty()
                || version.id.len() > 64
                || !version
                    .id
                    .bytes()
                    .all(|b| b.is_ascii_alphanumeric() || b == b'.' || b == b'_' || b == b'-')
            {
                return Err(ManifestError::InvalidVersionId);
            }

            if !ids.insert(version.id.as_str()) {
                return Err(ManifestError::DuplicateVersionId);
            }

            if !version.url.starts_with(OFFICIAL_METADATA_PREFIX)
                || version.url.contains('@')
                || version.url.contains('\\')
                || version.url.contains('#')
            {
                return Err(ManifestError::UntrustedMetadataUrl);
            }

            if version.sha1.len() != 40 || !version.sha1.bytes().all(|b| b.is_ascii_hexdigit()) {
                return Err(ManifestError::InvalidSha1);
            }
        }

        if !ids.contains(manifest.latest.release.as_str())
            || !ids.contains(manifest.latest.snapshot.as_str())
        {
            return Err(ManifestError::LatestVersionMissing);
        }

        Ok(manifest)
    }

    pub fn find(&self, id: &str) -> Option<&VersionEntry> {
        self.versions.iter().find(|entry| entry.id == id)
    }
}

#[cfg(test)]
mod tests {
    use super::{ManifestError, VersionManifest};

    const VALID: &str = r#"{
        "latest":{"release":"1.21.1","snapshot":"24w01a"},
        "versions":[
            {
                "id":"1.21.1",
                "type":"release",
                "url":"https://piston-meta.mojang.com/v1/packages/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/1.21.1.json",
                "releaseTime":"2024-08-08T12:00:00+00:00",
                "sha1":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "complianceLevel":1
            },
            {
                "id":"24w01a",
                "type":"snapshot",
                "url":"https://piston-meta.mojang.com/v1/packages/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/24w01a.json",
                "releaseTime":"2024-01-01T12:00:00+00:00",
                "sha1":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "complianceLevel":1
            }
        ]
    }"#;

    #[test]
    fn parses_official_manifest_and_finds_version() {
        let manifest = VersionManifest::parse(VALID).unwrap();
        assert_eq!(manifest.latest.release, "1.21.1");
        assert_eq!(manifest.find("1.21.1").unwrap().version_type, "release");
    }

    #[test]
    fn rejects_untrusted_metadata_host() {
        let hostile = VALID.replace(
            "https://piston-meta.mojang.com/",
            "https://example.invalid/",
        );
        assert_eq!(
            VersionManifest::parse(&hostile).unwrap_err(),
            ManifestError::UntrustedMetadataUrl
        );
    }

    #[test]
    fn rejects_duplicate_ids() {
        let duplicate = VALID.replace("\"id\":\"24w01a\"", "\"id\":\"1.21.1\"");
        assert_eq!(
            VersionManifest::parse(&duplicate).unwrap_err(),
            ManifestError::DuplicateVersionId
        );
    }

    #[test]
    fn rejects_manifest_with_missing_latest_release() {
        let missing = VALID.replace("\"release\":\"1.21.1\"", "\"release\":\"9.9\"");
        assert_eq!(
            VersionManifest::parse(&missing).unwrap_err(),
            ManifestError::LatestVersionMissing
        );
    }
}
