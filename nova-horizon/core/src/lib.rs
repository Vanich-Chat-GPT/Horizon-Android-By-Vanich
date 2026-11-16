pub mod chunk_queue;
pub mod frame_time;

use jni::objects::JObject;
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
        "NOVA Rust Core 0.1.0-dev · arch={} · modules=frame-time,priority-queue",
        std::env::consts::ARCH
    );

    match env.new_string(status) {
        Ok(value) => value.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}
