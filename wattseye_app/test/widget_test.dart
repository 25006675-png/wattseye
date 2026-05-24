import 'package:flutter_test/flutter_test.dart';
import 'package:wattseye_app/main.dart';

void main() {
  testWidgets('shows WattsEye dashboard smoke test', (tester) async {
    await tester.pumpWidget(const WattsEyeApp());

    expect(find.text('Dashboard'), findsWidgets);
    expect(find.text('Current power'), findsOneWidget);
    expect(find.text('Coach'), findsOneWidget);
  });
}
