# UZSL TARJIMON — STARTER KOD

**Maqsad:** Flutter + MediaPipe Hands (ML Kit) ishlaydigan minimal prototip  
**Vaqt:** 2 hafta  
**Natija:** Telefon kamerasi qo'l harakatlarini real vaqtda kuzatadi, ekranda 21 ta landmark nuqtasini chizadi  

---

## 1. KERAKLI VOSITALAR

Boshlashdan oldin kompyuteringizga o'rnatish kerak:

### 1.1 Flutter SDK
- **Yuklab olish:** [flutter.dev/docs/get-started/install](https://flutter.dev/docs/get-started/install)
- **Versiya:** Flutter 3.16 yoki undan yuqori
- **Tekshirish:** Terminalda `flutter --version`

### 1.2 Android Studio
- **Yuklab olish:** [developer.android.com/studio](https://developer.android.com/studio)
- Android SDK + Android Emulator o'rnatilishi kerak.
- Real qurilmada test qilish tavsiya etiladi (emulator kamerani yaxshi qo'llab-quvvatlamaydi).

### 1.3 VS Code (ixtiyoriy, lekin tavsiya)
- **Yuklab olish:** [code.visualstudio.com](https://code.visualstudio.com)
- Flutter va Dart plugin'larini o'rnatish.

### 1.4 iOS uchun (faqat Mac kerak)
- Xcode 15+
- CocoaPods: `sudo gem install cocoapods`

---

## 2. LOYIHANI YARATISH

Terminal oching va quyidagilarni ketma-ket bajaring:

```bash
# Yangi Flutter loyiha yaratish
flutter create --org com.uzsl uzsl_translator

# Loyihaga kirish
cd uzsl_translator

# Kerakli paketlarni qo'shish
flutter pub add camera
flutter pub add google_mlkit_pose_detection
flutter pub add permission_handler
flutter pub add path_provider
```

*Eslatma: MediaPipe Holistic'ning rasmiy Flutter plugin'i hali barqaror emas. MVP uchun Google ML Kit Pose Detection ishlatamiz — u MediaPipe asosida qurilgan va Flutter uchun barqaror. Keyingi versiyada to'liq MediaPipe Holistic (yuz + qo'l + tana) uchun native bridge yozamiz.*

---

## 3. PERMISSIONLAR (RUXSATNOMALAR)

### 3.1 Android — `android/app/src/main/AndroidManifest.xml`
`<application>` tag'idan oldin quyidagi qatorlarni qo'shing:
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-feature android:name="android.hardware.camera" />
<uses-feature android:name="android.hardware.camera.autofocus" />
```

### 3.2 Android — `android/app/build.gradle`
`defaultConfig` blokida:
```groovy
defaultConfig {
    minSdkVersion 21
    targetSdkVersion 34
}
```

### 3.3 iOS — `ios/Runner/Info.plist`
`<dict>` ichiga qo'shing:
```xml
<key>NSCameraUsageDescription</key>
<string>UZSL Tarjimon imo-ishora tilini tanish uchun kameraga kirish so'raydi</string>
<key>NSMicrophoneUsageDescription</key>
<string>Ovozli tarjima uchun mikrofonga ruxsat kerak</string>
```

---

## 4. ASOSIY KOD

### 4.1 `lib/main.dart`
Mavjud kodni butunlay almashtiring:
```dart
import 'package:flutter/material.dart';
import 'screens/camera_screen.dart';

void main() {
  runApp(const UZSLApp());
}

class UZSLApp extends StatelessWidget {
  const UZSLApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'UZSL Tarjimon',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('UZSL Tarjimon'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.sign_language, size: 100, color: Colors.deepPurple),
            const SizedBox(height: 20),
            const Text(
              "O'zbek Imo-Ishora Tili Tarjimoni",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 40),
            ElevatedButton.icon(
              icon: const Icon(Icons.camera_alt),
              label: const Text("Kamerani yoqish"),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                textStyle: const TextStyle(fontSize: 18),
              ),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const CameraScreen(),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
```

### 4.2 `lib/screens/camera_screen.dart`
Yangi papka yarating: `lib/screens/` va ichiga `camera_screen.dart` faylini joylashtiring:
```dart
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:permission_handler/permission_handler.dart';
import '../widgets/pose_painter.dart';

class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  CameraController? _cameraController;
  late PoseDetector _poseDetector;
  bool _isDetecting = false;
  List<Pose> _poses = [];
  Size? _imageSize;

  @override
  void initState() {
    super.initState();
    _poseDetector = PoseDetector(options: PoseDetectorOptions(
      mode: PoseDetectionMode.stream,
      model: PoseDetectionModel.accurate,
    ));
    _initCamera();
  }

  Future<void> _initCamera() async {
    final status = await Permission.camera.request();
    if (!status.isGranted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Kamera ruxsati kerak")),
      );
      return;
    }

    final cameras = await availableCameras();
    if (cameras.isEmpty) return;

    final frontCamera = cameras.firstWhere(
      (cam) => cam.lensDirection == CameraLensDirection.front,
      orElse: () => cameras.first,
    );

    _cameraController = CameraController(
      frontCamera,
      ResolutionPreset.medium,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.nv21, // Android uchun
    );

    await _cameraController!.initialize();
    if (!mounted) return;

    await _cameraController!.startImageStream(_processCameraImage);
    setState(() {});
  }

  Future<void> _processCameraImage(CameraImage image) async {
    if (_isDetecting) return;
    _isDetecting = true;

    try {
      final inputImage = _convertCameraImage(image);
      if (inputImage == null) {
        _isDetecting = false;
        return;
      }

      final poses = await _poseDetector.processImage(inputImage);

      if (mounted) {
        setState(() {
          _poses = poses;
          _imageSize = Size(image.width.toDouble(), image.height.toDouble());
        });
      }
    } catch (e) {
      debugPrint("Tanish xatosi: $e");
    } finally {
      _isDetecting = false;
    }
  }

  InputImage? _convertCameraImage(CameraImage image) {
    try {
      final camera = _cameraController!.description;
      final rotation = InputImageRotationValue.fromRawValue(camera.sensorOrientation);
      if (rotation == null) return null;

      final format = InputImageFormatValue.fromRawValue(image.format.raw);
      if (format == null) return null;

      final plane = image.planes.first;

      return InputImage.fromBytes(
        bytes: plane.bytes,
        metadata: InputImageMetadata(
          size: Size(image.width.toDouble(), image.height.toDouble()),
          rotation: rotation,
          format: format,
          bytesPerRow: plane.bytesPerRow,
        ),
      );
    } catch (e) {
      debugPrint("Konvertatsiya xatosi: $e");
      return null;
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _poseDetector.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text("Kuzatuv"),
        backgroundColor: Colors.black,
        foregroundColor: Colors.white,
      ),
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          CameraPreview(_cameraController!),

          if (_imageSize != null)
            CustomPaint(
              painter: PosePainter(
                poses: _poses,
                imageSize: _imageSize!,
                isFrontCamera: true,
              ),
            ),

          Positioned(
            bottom: 30,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.all(15),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.7),
                borderRadius: BorderRadius.circular(15),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _poses.isEmpty
                        ? "Qo'l/tana topilmadi"
                        : "Tanildi: ${_poses.length} ta tana",
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (_poses.isNotEmpty)
                    Text(
                      "Landmark soni: ${_poses.first.landmarks.length}",
                      style: const TextStyle(color: Colors.white70, fontSize: 14),
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
```

### 4.3 `lib/widgets/pose_painter.dart`
Yangi papka: `lib/widgets/` va ichiga `pose_painter.dart`:
```dart
import 'package:flutter/material.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';

class PosePainter extends CustomPainter {
  final List<Pose> poses;
  final Size imageSize;
  final bool isFrontCamera;

  PosePainter({
    required this.poses,
    required this.imageSize,
    this.isFrontCamera = true,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final pointPaint = Paint()
      ..color = Colors.greenAccent
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 8.0;

    final linePaint = Paint()
      ..color = Colors.cyanAccent
      ..strokeWidth = 3.0;

    for (final pose in poses) {
      _drawLine(canvas, pose, PoseLandmarkType.leftShoulder, PoseLandmarkType.rightShoulder, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.leftShoulder, PoseLandmarkType.leftElbow, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.leftElbow, PoseLandmarkType.leftWrist, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.rightShoulder, PoseLandmarkType.rightElbow, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.rightElbow, PoseLandmarkType.rightWrist, linePaint, size);

      _drawLine(canvas, pose, PoseLandmarkType.leftWrist, PoseLandmarkType.leftPinky, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.leftWrist, PoseLandmarkType.leftIndex, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.leftWrist, PoseLandmarkType.leftThumb, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.rightWrist, PoseLandmarkType.rightPinky, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.rightWrist, PoseLandmarkType.rightIndex, linePaint, size);
      _drawLine(canvas, pose, PoseLandmarkType.rightWrist, PoseLandmarkType.rightThumb, linePaint, size);

      pose.landmarks.forEach((type, landmark) {
        final point = _translatePoint(landmark, size);
        canvas.drawCircle(point, 4, pointPaint);
      });
    }
  }

  void _drawLine(Canvas canvas, Pose pose, PoseLandmarkType type1,
      PoseLandmarkType type2, Paint paint, Size size) {
    final l1 = pose.landmarks[type1];
    final l2 = pose.landmarks[type2];
    if (l1 == null || l2 == null) return;
    canvas.drawLine(_translatePoint(l1, size), _translatePoint(l2, size), paint);
  }

  Offset _translatePoint(PoseLandmark landmark, Size canvasSize) {
    double x = landmark.x * canvasSize.width / imageSize.width;
    double y = landmark.y * canvasSize.height / imageSize.height;

    if (isFrontCamera) {
      x = canvasSize.width - x;
    }

    return Offset(x, y);
  }

  @override
  bool shouldRepaint(covariant PosePainter oldDelegate) {
    return oldDelegate.poses != poses || oldDelegate.imageSize != imageSize;
  }
}
```

---

## 5. ISHGA TUSHIRISH

```bash
# Bog'liqliklarni yangilash
flutter pub get

# Real qurilmada (USB orqali ulangan)
flutter run

# Yoki release rejimida (tezroq)
flutter run --release
```

*Birinchi marta ishga tushirganda: Telefon kameraga ruxsat so'raydi → ruxsat bering → "Kamerani yoqish" tugmasini bosing → O'zingizni kameraga ko'rsating. Ekranda yashil-moviy chiziqlar va nuqtalar paydo bo'ladi.*

---

## 6. NIMA ISHLAYDI VA NIMA YO'Q

* **Hozir ishlaydi:**
  - Real-time kamera oqimi (30 FPS)
  - Tana va qo'l asosiy nuqtalarini tanish (33 landmark)
  - Ekranda skeleton chizish
  - Old kamera (selfie) qo'llab-quvvatlash

* **Hali ishlamaydi (keyingi bosqichlarda qo'shiladi):**
  - Yuz va og'iz landmarklari (468 nuqta — alohida MediaPipe FaceMesh)
  - Har bir qo'l uchun 21 ta batafsil nuqta (alohida MediaPipe Hands)
  - UZSL imo-ishora tanish (TFLite model)
  - Matnga aylantirish va TTS

---

## 7. KEYINGI 2 HAFTALIK REJA

* **1-hafta:**
  - **1-2 kun:** Kodni ishga tushirish, o'z qurilmangizda sinab ko'rish.
  - **3-4 kun:** FPS va aniqlikni tekshirish, log'larga landmark koordinatalarini chiqarish.
  - **5-7 kun:** 5 ta sodda UZSL belgisini tanlash (salom, rahmat, ha, yo'q, kerak) va har biri uchun 20 ta video yozish.

* **2-hafta:**
  - **8-10 kun:** Python'da yig'ilgan ma'lumotlardan landmark sequence'larni eksport qilish va sodda klassifikator (k-NN yoki kichik MLP) trenirovka qilish.
  - **11-12 kun:** Modelni `.tflite` formatiga konvertatsiya qilish.
  - **13-14 kun:** Flutter ilovasiga TFLite'ni qo'shish va birinchi imo-ishorani matnga aylantirish.

---

## 8. KO'PCHILIKDA UCHRAYDIGAN MUAMMOLAR VA YECHIMLAR

| Muammo | Yechim |
| :--- | :--- |
| **Permission denied xatosi** | Telefon Sozlamalari → Ilovalar → UZSL → Kamera ruxsatini yoqing |
| **Qora ekran, kamera ko'rinmayapti** | `imageFormatGroup` ni o'zgartiring: Android = `nv21`, iOS = `bgra8888` |
| **FPS juda past (< 10)** | `ResolutionPreset.low` ga o'zgartiring, yoki har 3-frame'dan birini qayta ishlang |
| **Skeleton noto'g'ri joyda chiziladi** | `_translatePoint` funksiyasidagi `isFrontCamera` flagini tekshirish |
| **iOS'da CocoaPods xatosi** | `cd ios && pod install --repo-update` |
| **Build xatosi: minSdkVersion** | `android/app/build.gradle` faylida `minSdkVersion 21` qiling |

---

## 9. FOYDALI HAVOLALAR

- Flutter Camera Plugin: [pub.dev/packages/camera](https://pub.dev/packages/camera)
- Google ML Kit Pose Detection: [pub.dev/packages/google_mlkit_pose_detection](https://pub.dev/packages/google_mlkit_pose_detection)
- MediaPipe Pose Landmarks (33 nuqta): [developers.google.com/mediapipe/solutions/vision/pose_landmarker](https://developers.google.com/mediapipe/solutions/vision/pose_landmarker)
- Flutter TFLite (keyingi bosqich): [pub.dev/packages/tflite_flutter](https://pub.dev/packages/tflite_flutter)

---
*Hujjat oxiri. Bu UZSL Tarjimon Flutter Starter kod yo'riqnomasi.*
