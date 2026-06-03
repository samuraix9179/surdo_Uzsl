package com.uzsl.uzsl_translator

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import com.google.mediapipe.tasks.vision.holisticlandmarker.HolisticLandmarkerResult
import com.google.mediapipe.tasks.components.containers.NormalizedLandmark

class MainActivity : FlutterActivity() {

    private val methodChannelName = "uzsl/holistic"
    private val eventChannelName = "uzsl/holistic_stream"

    private var processor: HolisticProcessor? = null
    private var eventSink: EventChannel.EventSink? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        EventChannel(flutterEngine.dartExecutor.binaryMessenger, eventChannelName)
            .setStreamHandler(object : EventChannel.StreamHandler {
                override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                    eventSink = events
                }

                override fun onCancel(arguments: Any?) {
                    eventSink = null
                }
            })

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, methodChannelName)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "init" -> {
                        initProcessor()
                        result.success(true)
                    }
                    "process" -> {
                        val bytes = call.argument<ByteArray>("bytes")
                        val width = call.argument<Int>("width") ?: 0
                        val height = call.argument<Int>("height") ?: 0
                        val rotation = call.argument<Int>("rotation") ?: 0
                        val timestamp = (call.argument<Number>("timestamp") ?: 0L).toLong()
                        if (bytes != null) {
                            processor?.process(bytes, width, height, rotation, timestamp)
                        }
                        result.success(true)
                    }
                    "dispose" -> {
                        processor?.close()
                        processor = null
                        result.success(true)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    private fun initProcessor() {
        if (processor != null) return
        processor = HolisticProcessor(
            context = this,
            modelPath = "flutter_assets/assets/holistic_landmarker.task",
            onResult = { res, w, h -> sendResult(res, w, h) },
            onError = { msg ->
                runOnUiThread {
                    eventSink?.success(mapOf("error" to msg))
                }
            },
        )
    }

    /** Natijani Flutter'ga oddiy Map/List ko'rinishida jo'natadi (normalized 0..1 koordinatalar). */
    private fun sendResult(result: HolisticLandmarkerResult, width: Int, height: Int) {
        val payload = HashMap<String, Any>()
        payload["imageWidth"] = width
        payload["imageHeight"] = height
        payload["pose"] = encode(result.poseLandmarks())
        payload["face"] = encode(result.faceLandmarks())
        payload["leftHand"] = encode(result.leftHandLandmarks())
        payload["rightHand"] = encode(result.rightHandLandmarks())

        runOnUiThread {
            eventSink?.success(payload)
        }
    }

    /** NormalizedLandmark ro'yxatini [x0,y0,x1,y1,...] formatdagi flat list'ga aylantiradi. */
    private fun encode(landmarks: List<NormalizedLandmark>?): List<Double> {
        if (landmarks == null) return emptyList()
        val out = ArrayList<Double>(landmarks.size * 2)
        for (lm in landmarks) {
            out.add(lm.x().toDouble())
            out.add(lm.y().toDouble())
        }
        return out
    }
}
