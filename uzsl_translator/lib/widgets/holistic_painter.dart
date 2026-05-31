import 'package:flutter/material.dart';
import '../services/holistic_service.dart';

/// MediaPipe Holistic natijasini (543 nuqta) ekranga chizadi:
/// - tana skeletoni (yashil),
/// - yuz nuqtalari/mesh (oq mayda nuqtalar),
/// - chap qo'l (zangori), o'ng qo'l (qizg'ish) — 21 tadan bo'g'im.
class HolisticPainter extends CustomPainter {
  final HolisticResult? result;
  final bool isFrontCamera;

  HolisticPainter({required this.result, this.isFrontCamera = true});

  // MediaPipe Pose ulanishlari (33 nuqtali model uchun asosiy skeleton).
  static const List<List<int>> _poseConnections = [
    [11, 12], [11, 13], [13, 15], [12, 14], [14, 16], // yelka-bilak
    [11, 23], [12, 24], [23, 24], // tana
    [23, 25], [25, 27], [24, 26], [26, 28], // oyoq
  ];

  // MediaPipe Hand ulanishlari (21 nuqta): barmoqlar.
  static const List<List<int>> _handConnections = [
    [0, 1], [1, 2], [2, 3], [3, 4], // bosh barmoq
    [0, 5], [5, 6], [6, 7], [7, 8], // ko'rsatkich
    [5, 9], [9, 10], [10, 11], [11, 12], // o'rta
    [9, 13], [13, 14], [14, 15], [15, 16], // nomsiz
    [13, 17], [17, 18], [18, 19], [19, 20], [0, 17], // jimjiloq + kaft
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final r = result;
    if (r == null) return;

    // Tana skeletoni.
    _drawConnections(canvas, size, r.pose, _poseConnections, Colors.greenAccent, 3.0);
    _drawPoints(canvas, size, r.pose, Colors.green, 4.0);

    // Yuz mesh nuqtalari (468 ta) — mayda oq nuqtalar.
    _drawPoints(canvas, size, r.face, Colors.white70, 1.3);

    // Chap qo'l (zangori).
    _drawConnections(canvas, size, r.leftHand, _handConnections, Colors.lightBlueAccent, 2.5);
    _drawPoints(canvas, size, r.leftHand, Colors.blue, 4.0);

    // O'ng qo'l (qizg'ish).
    _drawConnections(canvas, size, r.rightHand, _handConnections, Colors.orangeAccent, 2.5);
    _drawPoints(canvas, size, r.rightHand, Colors.deepOrange, 4.0);
  }

  void _drawPoints(
      Canvas canvas, Size size, List<double> flat, Color color, double radius) {
    final paint = Paint()
      ..color = color
      ..strokeCap = StrokeCap.round;
    for (int i = 0; i + 1 < flat.length; i += 2) {
      canvas.drawCircle(_pt(flat[i], flat[i + 1], size), radius, paint);
    }
  }

  void _drawConnections(Canvas canvas, Size size, List<double> flat,
      List<List<int>> connections, Color color, double strokeWidth) {
    if (flat.isEmpty) return;
    final paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;
    final count = flat.length ~/ 2;
    for (final c in connections) {
      if (c[0] >= count || c[1] >= count) continue;
      final p1 = _pt(flat[c[0] * 2], flat[c[0] * 2 + 1], size);
      final p2 = _pt(flat[c[1] * 2], flat[c[1] * 2 + 1], size);
      canvas.drawLine(p1, p2, paint);
    }
  }

  /// Normalized (0..1) koordinatani ekran pikseliga aylantiradi.
  Offset _pt(double nx, double ny, Size size) {
    double x = nx * size.width;
    double y = ny * size.height;
    if (isFrontCamera) {
      x = size.width - x; // selfie kamera oynasi (mirror).
    }
    return Offset(x, y);
  }

  @override
  bool shouldRepaint(covariant HolisticPainter oldDelegate) {
    return oldDelegate.result != result;
  }
}
