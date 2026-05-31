package com.uzsl.uzsl_translator

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.framework.image.MPImage
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.core.Delegate
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.holisticlandmarker.HolisticLandmarker
import com.google.mediapipe.tasks.vision.holisticlandmarker.HolisticLandmarkerResult
import java.io.ByteArrayOutputStream

/**
 * MediaPipe Holistic Landmarker'ni LIVE_STREAM rejimida ishlatadi.
 * Har bir kamera frame'i uchun 543 ta nuqta (33 tana + 468 yuz + 2x21 qo'l) qaytaradi.
 */
class HolisticProcessor(
    context: Context,
    modelPath: String,
    private val onResult: (HolisticLandmarkerResult, Int, Int) -> Unit,
    private val onError: (String) -> Unit,
) {
    private var landmarker: HolisticLandmarker? = null

    // Joriy frame o'lchamlari (natija callback'ida ishlatish uchun).
    @Volatile private var lastWidth = 0
    @Volatile private var lastHeight = 0

    init {
        try {
            val baseOptions = BaseOptions.builder()
                .setModelAssetPath(modelPath)
                .setDelegate(Delegate.GPU)
                .build()

            val options = HolisticLandmarker.HolisticLandmarkerOptions.builder()
                .setBaseOptions(baseOptions)
                .setRunningMode(RunningMode.LIVE_STREAM)
                .setMinFaceDetectionConfidence(0.5f)
                .setMinPoseDetectionConfidence(0.5f)
                .setMinHandLandmarksConfidence(0.5f)
                .setResultListener { result: HolisticLandmarkerResult, _: MPImage ->
                    onResult(result, lastWidth, lastHeight)
                }
                .setErrorListener { e -> onError(e.message ?: "MediaPipe xatosi") }
                .build()

            landmarker = HolisticLandmarker.createFromOptions(context, options)
        } catch (e: Exception) {
            onError("Holistic init xatosi: ${e.message}")
        }
    }

    /**
     * NV21 (YUV420) baytlarni qabul qiladi, Bitmap'ga aylantiradi va
     * kerakli burchakka aylantirib MediaPipe'ga uzatadi.
     */
    fun process(
        nv21: ByteArray,
        width: Int,
        height: Int,
        rotationDegrees: Int,
        timestampMs: Long,
    ) {
        val lm = landmarker ?: return
        try {
            val bitmap = nv21ToBitmap(nv21, width, height) ?: return
            val rotated = if (rotationDegrees != 0) rotateBitmap(bitmap, rotationDegrees) else bitmap

            lastWidth = rotated.width
            lastHeight = rotated.height

            val mpImage: MPImage = BitmapImageBuilder(rotated).build()
            lm.detectAsync(mpImage, timestampMs)
        } catch (e: Exception) {
            onError("Frame process xatosi: ${e.message}")
        }
    }

    private fun nv21ToBitmap(nv21: ByteArray, width: Int, height: Int): Bitmap? {
        return try {
            val yuvImage = YuvImage(nv21, ImageFormat.NV21, width, height, null)
            val out = ByteArrayOutputStream()
            yuvImage.compressToJpeg(Rect(0, 0, width, height), 90, out)
            val jpegBytes = out.toByteArray()
            BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size)
        } catch (e: Exception) {
            null
        }
    }

    private fun rotateBitmap(bitmap: Bitmap, degrees: Int): Bitmap {
        val matrix = Matrix().apply { postRotate(degrees.toFloat()) }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    }

    fun close() {
        landmarker?.close()
        landmarker = null
    }
}
