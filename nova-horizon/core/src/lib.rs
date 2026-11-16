pub mod chunk_queue;
pub mod frame_time;
pub mod version_manifest;

use jni::objects::{JObject, JString};
use jni::sys::jstring;
use jni::JNIEnv;

/// JNI status endpoint used by the Android diagnostics screen.
/// This reports the native module only; it does not claim that a game runtime exists.
#[no_mangle]
pub extern "system" fn Java_dev_nova_horizon_NativeBridge_nativeCoreStatus(
    mut env: JNIEnv,
    _this: JObject,
) -> jstring {
    let status = format!(
        "NOVA Rust Core 0.1.0-dev · arch={} · modules=frame-time,priority-queue,version-manifest",
        std::env::consts::ARCH
    );

    match env.new_string(status) {
        Ok(value) => value.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Validates the official Mojang version index and returns a compact JNI-safe result.
/// The parser rejects unknown metadata hosts and malformed or duplicate version entries.
#[no_mangle]
pub extern "system" fn Java_dev_nova_horizon_NativeBridge_nativeInspectVersionManifest(
    mut env: JNIEnv,
    _this: JObject,
    json: JString,
) -> jstring {
    let response = match env.get_string(&json) {
        Ok(value) => {
            let payload: String = value.into();
            match version_manifest::VersionManifest::parse(&payload) {
                Ok(manifest) => format!(
                    "OK|{}|{}|{}",
                    manifest.latest.release,
                    manifest.latest.snapshot,
                    manifest.versions.len()
                ),
                Err(error) => format!("ERROR|{:?}", error),
            }
        }
        Err(_) => "ERROR|InvalidJavaString".to_owned(),
    };

    match env.new_string(response) {
        Ok(value) => value.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}
