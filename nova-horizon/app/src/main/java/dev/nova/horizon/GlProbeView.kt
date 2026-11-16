package dev.nova.horizon

import android.content.Context
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.os.Handler
import android.os.Looper
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

internal data class GlProbeResult(
    val renderer: String,
    val vendor: String,
    val version: String,
    val shadingLanguage: String,
    val extensionCount: Int
)

/**
 * Creates a real EGL/OpenGL ES context and reads strings from that context.
 * It intentionally does not infer a GPU model from the Android device name.
 */
internal class GlProbeView(
    context: Context,
    private val onProbe: (GlProbeResult) -> Unit
) : GLSurfaceView(context) {

    private val mainHandler = Handler(Looper.getMainLooper())

    init {
        setEGLContextClientVersion(2)
        preserveEGLContextOnPause = false
        setRenderer(object : Renderer {
            override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
                val extensions = GLES20.glGetString(GLES20.GL_EXTENSIONS)
                    ?.split(' ')
                    ?.filter { it.isNotBlank() }
                    ?.toSet()
                    .orEmpty()

                val result = GlProbeResult(
                    renderer = GLES20.glGetString(GLES20.GL_RENDERER) ?: "Неизвестно",
                    vendor = GLES20.glGetString(GLES20.GL_VENDOR) ?: "Неизвестно",
                    version = GLES20.glGetString(GLES20.GL_VERSION) ?: "Неизвестно",
                    shadingLanguage = GLES20.glGetString(GLES20.GL_SHADING_LANGUAGE_VERSION)
                        ?: "Неизвестно",
                    extensionCount = extensions.size
                )
                mainHandler.post { onProbe(result) }
            }

            override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) = Unit
            override fun onDrawFrame(gl: GL10?) = Unit
        })
        renderMode = RENDERMODE_WHEN_DIRTY
        requestRender()
    }
}
