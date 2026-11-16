pub mod chunk_queue;
pub mod download_state;
pub mod frame_time;
pub mod version_manifest;
pub mod version_metadata;

use jni::objects::{JObject, JString};
use jni::sys::jstring;
use jni::JNIEnv;

/// JNI status endpoint used by the Android diagnostics screen.
#[no_mangle]
pub extern "system" fn Java_dev_nova_horizon_NativeBridge_nativeCoreStatus(
    env: JNIEnv,
    _this: JObject,
) -> jstring {
    let status = format!(
        "NOVA Rust Core 0.1.0-dev · arch={} · modules=frame-time,priority-queue,download-state,version-manifest,version-metadata",
        std::env::consts::ARCH
    );

    match env.new_string(status) {
        Ok(value) => value.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Validate an official Mojang version manifest and return a normalized JSON catalog.
#[no_mangle]
pub extern "system" fn Java_dev_nova_horizon_NativeBridge_nativeParseVersionCatalog(
    mut env: JNIEnv,
    _this: JObject,
    json: JString,
) -> jstring {
    let response = match env.get_string(&json) {
        Ok(value) => {
            let payload: String = value.into();
            match version_manifest::VersionManifest::parse(&payload) {
                Ok(manifest) => serde_json::to_string(&manifest)
                    .unwrap_or_else(|_| "{\"ok\":false,\"error\":\"SerializeFailed\"}".to_owned()),
                Err(error) => serde_json::json!({
                    "ok": false,
                    "error": format!("{:?}", error)
                })
                .to_string(),
            }
        }
        Err(_) => "{\"ok\":false,\"error\":\"InvalidJavaString\"}".to_owned(),
    };

    match env.new_string(response) {
        Ok(value) => value.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Validate a selected version's metadata before the Android installer can use it.
#[no_mangle]
pub extern "system" fn Java_dev_nova_horizon_NativeBridge_nativeInspectVersionMetadata(
    mut env: JNIEnv,
    _this: JObject,
    json: JString,
    expected_id: JString,
) -> jstring {
    let response = match env.get_string(&json) {
        Ok(payload) => {
            let payload: String = payload.into();
            match env.get_string(&expected_id) {
                Ok(expected) => {
                    let expected_id: String = expected.into();
                    match version_metadata::VersionMetadata::parse(&payload, &expected_id) {
                        Ok(metadata) => {
                            let java_major = metadata
                                .java_version
                                .as_ref()
                                .map(|runtime| runtime.major_version);
                            let asset_index_id =
                                metadata.asset_index.as_ref().map(|index| index.id.clone());
                            let client_size =
                                metadata.client_download().map(|artifact| artifact.size);
                            let library_count = metadata.library_count();

                            serde_json::json!({
                                "ok": true,
                                "id": metadata.id,
                                "versionType": metadata.version_type,
                                "mainClass": metadata.main_class,
                                "javaMajor": java_major,
                                "assetIndexId": asset_index_id,
                                "clientSize": client_size,
                                "libraryCount": library_count
                            })
                            .to_string()
                        }
                        Err(error) => serde_json::json!({
                            "ok": false,
                            "error": format!("{:?}", error)
                        })
                        .to_string(),
                    }
                }
                Err(_) => "{\"ok\":false,\"error\":\"InvalidExpectedVersionId\"}".to_owned(),
            }
        }
        Err(_) => "{\"ok\":false,\"error\":\"InvalidJavaString\"}".to_owned(),
    };

    match env.new_string(response) {
        Ok(value) => value.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}
