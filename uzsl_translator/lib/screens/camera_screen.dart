import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:permission_handler/permission_handler.dart';
import '../services/holistic_service.dart';
import '../widgets/holistic_painter.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _cameraController;
  final HolisticService _holistic = HolisticService();
  StreamSubscription<dynamic>? _resultSub;

  bool _isBusy = false;
  bool _isFront = true;
  HolisticResult? _result;
  String? _error;
  int _frameCount = 0;

  @override
  void initState() {
    super.initState();
    _initEverything();
  }

  Future<void> _initEverything() async {
    final status = await Permission.camera.request();
    if (!status.isGranted) {
      if (!mounted) return;
      setState(() => _error = "Kamera ruxsati kerak");
      return;
    }

    // Native MediaPipe Holistic'ni ishga tushiramiz.
    try {
      await _holistic.init();
      _resultSub = _holistic.results.listen((event) {
        if (!mounted) return;
        if (event is HolisticResult) {
          setState(() => _result = event);
        } else if (event is Map && event['error'] != null) {
          debugPrint("Holistic xato: ${event['error']}");
        }
      });
    } catch (e) {
      if (mounted) setState(() => _error = "Holistic init: $e");
      return;
    }

    await _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    if (cameras.isEmpty) return;

    final camera = cameras.firstWhere(
      (cam) =>
          cam.lensDirection ==
          (_isFront ? CameraLensDirection.front : CameraLensDirection.back),
      orElse: () => cameras.first,
    );
    _isFront = camera.lensDirection == CameraLensDirection.front;

    _cameraController = CameraController(
      camera,
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.nv21, // Android: native uchun NV21.
    );

    await _cameraController!.initialize();
    if (!mounted) return;

    await _cameraController!.startImageStream(_onFrame);
    setState(() {});
  }

  void _onFrame(CameraImage image) async {
    if (_isBusy) return;
    _isBusy = true;
    try {
      final bytes = _yuv420ToNv21(image);
      final rotation = _cameraController!.description.sensorOrientation;
      await _holistic.process(
        bytes: bytes,
        width: image.width,
        height: image.height,
        rotation: rotation,
        timestamp: DateTime.now().millisecondsSinceEpoch,
      );
      _frameCount++;
    } catch (e) {
      debugPrint("Frame xato: $e");
    } finally {
      _isBusy = false;
    }
  }

  /// camera plugin NV21 so'ralganda bitta plane qaytaradi; uni to'g'ridan-to'g'ri uzatamiz.
  /// Ba'zi qurilmalarda YUV_420 ko'p plane bo'lishi mumkin — o'shanda NV21'ga yig'amiz.
  Uint8List _yuv420ToNv21(CameraImage image) {
    if (image.planes.length == 1) {
      return image.planes.first.bytes;
    }

    final int width = image.width;
    final int height = image.height;
    final Uint8List nv21 = Uint8List(width * height * 3 ~/ 2);

    // Y plane.
    final yPlane = image.planes[0];
    int pos = 0;
    for (int row = 0; row < height; row++) {
      final int rowStart = row * yPlane.bytesPerRow;
      nv21.setRange(pos, pos + width, yPlane.bytes, rowStart);
      pos += width;
    }

    // VU interleaved (NV21 = Y + VU).
    final uPlane = image.planes[1];
    final vPlane = image.planes[2];
    final int chromaRows = height ~/ 2;
    final int chromaCols = width ~/ 2;
    final int uvRowStride = uPlane.bytesPerRow;
    final int uvPixelStride = uPlane.bytesPerPixel ?? 1;
    for (int row = 0; row < chromaRows; row++) {
      for (int col = 0; col < chromaCols; col++) {
        final int uvIndex = row * uvRowStride + col * uvPixelStride;
        nv21[pos++] = vPlane.bytes[uvIndex];
        nv21[pos++] = uPlane.bytes[uvIndex];
      }
    }
    return nv21;
  }

  Future<void> _switchCamera() async {
    await _cameraController?.stopImageStream();
    await _cameraController?.dispose();
    _cameraController = null;
    _isFront = !_isFront;
    setState(() => _result = null);
    await _initCamera();
  }

  @override
  void dispose() {
    _resultSub?.cancel();
    _cameraController?.stopImageStream().catchError((_) {});
    _cameraController?.dispose();
    _holistic.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text("Xatolik")),
        body: Center(child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(_error!, textAlign: TextAlign.center),
        )),
      );
    }

    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final r = _result;
    return Scaffold(
      appBar: AppBar(
        title: const Text("Holistic kuzatuv"),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.cameraswitch),
            onPressed: _switchCamera,
          ),
        ],
      ),
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          CameraPreview(_cameraController!),

          CustomPaint(
            painter: HolisticPainter(result: r, isFrontCamera: _isFront),
          ),

          Positioned(
            bottom: 30,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.all(15),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.7),
                borderRadius: BorderRadius.circular(15),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    r == null
                        ? "Kuzatuv kutilmoqda..."
                        : "Jami nuqta: ${r.totalPoints} / 543",
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (r != null)
                    Text(
                      "Tana: ${r.pose.length ~/ 2} • Yuz: ${r.face.length ~/ 2} • "
                      "Chap qo'l: ${r.leftHand.length ~/ 2} • O'ng qo'l: ${r.rightHand.length ~/ 2}",
                      style: const TextStyle(color: Colors.white70, fontSize: 13),
                    ),
                  Text(
                    "Frame: $_frameCount",
                    style: const TextStyle(color: Colors.white38, fontSize: 11),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
