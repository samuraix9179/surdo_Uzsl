import 'package:flutter/services.dart';
/// Bitta to'plam holistic natijasi: tana, yuz va ikkala qo'l nuqtalari.
/// Har bir ro'yxat [x0, y0, x1, y1, ...] ko'rinishida, koordinatalar 0..1 oralig'ida.
class HolisticResult {
  final int imageWidth;
  final int imageHeight;
  final List<double> pose; // 33 nuqta -> 66 qiymat
  final List<double> face; // 468 nuqta -> 936 qiymat
  final List<double> leftHand; // 21 nuqta -> 42 qiymat
  final List<double> rightHand; // 21 nuqta -> 42 qiymat

  const HolisticResult({
    required this.imageWidth,
    required this.imageHeight,
    required this.pose,
    required this.face,
    required this.leftHand,
    required this.rightHand,
  });

  factory HolisticResult.fromMap(Map<dynamic, dynamic> map) {
    List<double> toList(dynamic v) =>
        (v as List?)?.map((e) => (e as num).toDouble()).toList() ?? <double>[];
    return HolisticResult(
      imageWidth: (map['imageWidth'] as num?)?.toInt() ?? 0,
      imageHeight: (map['imageHeight'] as num?)?.toInt() ?? 0,
      pose: toList(map['pose']),
      face: toList(map['face']),
      leftHand: toList(map['leftHand']),
      rightHand: toList(map['rightHand']),
    );
  }

  int get totalPoints =>
      (pose.length + face.length + leftHand.length + rightHand.length) ~/ 2;
}

/// Native MediaPipe Holistic Landmarker bilan bog'lovchi servis.
class HolisticService {
  static const _method = MethodChannel('uzsl/holistic');
  static const _events = EventChannel('uzsl/holistic_stream');

  Stream<dynamic>? _stream;

  Future<void> init() async {
    await _method.invokeMethod('init');
  }

  /// Kamera frame'ini (NV21 baytlar) native tomonga uzatadi.
  Future<void> process({
    required Uint8List bytes,
    required int width,
    required int height,
    required int rotation,
    required int timestamp,
  }) async {
    await _method.invokeMethod('process', {
      'bytes': bytes,
      'width': width,
      'height': height,
      'rotation': rotation,
      'timestamp': timestamp,
    });
  }

  /// Natijalar oqimi: HolisticResult yoki {'error': '...'} map'lari.
  Stream<dynamic> get results {
    _stream ??= _events.receiveBroadcastStream().map((event) {
      final map = event as Map<dynamic, dynamic>;
      if (map.containsKey('error')) {
        return map; // xato map'i
      }
      return HolisticResult.fromMap(map);
    });
    return _stream!;
  }

  Future<void> dispose() async {
    await _method.invokeMethod('dispose');
  }
}
