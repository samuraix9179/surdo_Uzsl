// UZSL Tarjimon uchun asosiy widget testi.

import 'package:flutter_test/flutter_test.dart';

import 'package:uzsl_translator/main.dart';

void main() {
  testWidgets('Bosh ekran yuklanadi', (WidgetTester tester) async {
    // Ilovani build qilamiz va bir frame chizamiz.
    await tester.pumpWidget(const UZSLApp());

    // Bosh ekrandagi sarlavha va tugma ko'rinishini tekshiramiz.
    expect(find.text("O'zbek Imo-Ishora Tili Tarjimoni"), findsOneWidget);
    expect(find.text('Kamerani yoqish'), findsOneWidget);
  });
}
