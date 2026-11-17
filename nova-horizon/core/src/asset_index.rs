use serde::{Deserialize, Serialize};
use std::collections::HashMap;

const MAX_INDEX_BYTES: usize = 32 * 1024 * 1024;
const MAX_OBJECTS: usize = 150_000;
const MAX_TOTAL_BYTES: u64 = 64 * 1024 * 1024 * 1024;

#[derive(Debug, Deserialize)]
struct AssetIndexDocument {
    objects: HashMap<String, AssetIndexObject>,
    #[serde(default, rename = "virtual")]
    virtual_assets: bool,
    #[serde(default, rename = "map_to_resources")]
    map_to_resources: bool,
}

#[derive(Debug, Deserialize)]
struct AssetIndexObject {
    hash: String,
    size: u64,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct PlannedAssetObject {
    pub hash: String,
    pub size: u64,
    pub url: String,
    pub relative_path: String,
    pub logical_keys: Vec<String>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct AssetIndexPlan {
    pub asset_index_id: String,
    pub objects: Vec<PlannedAssetObject>,
    pub total_download_bytes: u64,
    pub virtual_assets: bool,
    pub map_to_resources: bool,
}

#[derive(Debug, PartialEq, Eq)]
pub enum AssetIndexError {
    TooLarge,
    InvalidJson,
    InvalidIndexId,
    EmptyObjects,
    TooManyObjects,
    InvalidLogicalKey,
    InvalidSha1,
    InvalidSize,
    ConflictingHashSize,
    TotalSizeExceeded,
}

impl AssetIndexPlan {
    pub fn parse(json: &str, expected_id: &str) -> Result<Self, AssetIndexError> {
        if json.len() > MAX_INDEX_BYTES {
            return Err(AssetIndexError::TooLarge);
        }
        if !valid_index_id(expected_id) {
            return Err(AssetIndexError::InvalidIndexId);
        }

        let document: AssetIndexDocument =
            serde_json::from_str(json).map_err(|_| AssetIndexError::InvalidJson)?;
        if document.objects.is_empty() {
            return Err(AssetIndexError::EmptyObjects);
        }
        if document.objects.len() > MAX_OBJECTS {
            return Err(AssetIndexError::TooManyObjects);
        }

        let mut unique: HashMap<String, (u64, Vec<String>)> =
            HashMap::with_capacity(document.objects.len());
        for (logical_key, object) in document.objects {
            if !valid_logical_key(&logical_key) {
                return Err(AssetIndexError::InvalidLogicalKey);
            }
            if !valid_sha1(&object.hash) {
                return Err(AssetIndexError::InvalidSha1);
            }
            if object.size == 0 {
                return Err(AssetIndexError::InvalidSize);
            }

            let hash = object.hash.to_ascii_lowercase();
            match unique.get_mut(&hash) {
                Some((known_size, keys)) => {
                    if *known_size != object.size {
                        return Err(AssetIndexError::ConflictingHashSize);
                    }
                    keys.push(logical_key);
                }
                None => {
                    unique.insert(hash, (object.size, vec![logical_key]));
                }
            }
        }

        let mut objects = Vec::with_capacity(unique.len());
        let mut total_download_bytes = 0_u64;
        for (hash, (size, mut logical_keys)) in unique {
            total_download_bytes = total_download_bytes
                .checked_add(size)
                .ok_or(AssetIndexError::TotalSizeExceeded)?;
            if total_download_bytes > MAX_TOTAL_BYTES {
                return Err(AssetIndexError::TotalSizeExceeded);
            }
            logical_keys.sort();
            let prefix = &hash[..2];
            objects.push(PlannedAssetObject {
                hash: hash.clone(),
                size,
                url: format!("https://resources.download.minecraft.net/{prefix}/{hash}"),
                relative_path: format!("assets/objects/{prefix}/{hash}"),
                logical_keys,
            });
        }
        objects.sort_by(|left, right| left.hash.cmp(&right.hash));

        Ok(Self {
            asset_index_id: expected_id.to_owned(),
            objects,
            total_download_bytes,
            virtual_assets: document.virtual_assets,
            map_to_resources: document.map_to_resources,
        })
    }
}

fn valid_index_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'.' | b'_' | b'-'))
}

fn valid_sha1(value: &str) -> bool {
    value.len() == 40 && value.bytes().all(|byte| byte.is_ascii_hexdigit())
}

fn valid_logical_key(value: &str) -> bool {
    !value.is_empty()
        && !value.starts_with('/')
        && !value.contains('\\')
        && !value.bytes().any(|byte| byte.is_ascii_control())
        && value
            .split('/')
            .all(|part| !part.is_empty() && part != "." && part != "..")
}

#[cfg(test)]
mod tests {
    use super::{AssetIndexError, AssetIndexPlan};

    const VALID: &str = r#"{
        "virtual": true,
        "map_to_resources": false,
        "objects": {
            "minecraft/lang/en_us.json": {
                "hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "size": 10
            },
            "minecraft/lang/en_gb.json": {
                "hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "size": 10
            },
            "minecraft/sounds.json": {
                "hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "size": 5
            }
        }
    }"#;

    #[test]
    fn deduplicates_by_hash_and_preserves_logical_keys() {
        let plan = AssetIndexPlan::parse(VALID, "1.20").unwrap();
        assert_eq!(plan.objects.len(), 2);
        assert_eq!(plan.total_download_bytes, 15);
        assert!(plan.virtual_assets);
        let shared = plan
            .objects
            .iter()
            .find(|item| item.hash.starts_with('a'))
            .unwrap();
        assert_eq!(shared.logical_keys.len(), 2);
        assert_eq!(
            shared.relative_path,
            format!("assets/objects/aa/{}", shared.hash)
        );
        assert!(shared
            .url
            .starts_with("https://resources.download.minecraft.net/aa/"));
    }

    #[test]
    fn rejects_traversal_and_bad_hashes() {
        let hostile = VALID.replace("minecraft/lang/en_us.json", "../outside.json");
        assert_eq!(
            AssetIndexPlan::parse(&hostile, "1.20").unwrap_err(),
            AssetIndexError::InvalidLogicalKey
        );
        let bad_hash = VALID.replace("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "not-a-sha1");
        assert_eq!(
            AssetIndexPlan::parse(&bad_hash, "1.20").unwrap_err(),
            AssetIndexError::InvalidSha1
        );
    }

    #[test]
    fn rejects_invalid_sizes_and_conflicting_duplicate_hashes() {
        let invalid_size = VALID.replacen("\"size\": 10", "\"size\": 0", 1);
        assert_eq!(
            AssetIndexPlan::parse(&invalid_size, "1.20").unwrap_err(),
            AssetIndexError::InvalidSize
        );
        let conflicting = VALID.replacen("\"size\": 10", "\"size\": 11", 1);
        assert_eq!(
            AssetIndexPlan::parse(&conflicting, "1.20").unwrap_err(),
            AssetIndexError::ConflictingHashSize
        );
    }

    #[test]
    fn rejects_invalid_index_id() {
        assert_eq!(
            AssetIndexPlan::parse(VALID, "../1.20").unwrap_err(),
            AssetIndexError::InvalidIndexId
        );
    }
}
