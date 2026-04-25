// This is a basic Flutter widget test for Collection Uploader V2.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:collection_uploader/main.dart';

void main() {
  testWidgets('App loads successfully', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const CollectionUploaderApp());

    // Verify that the app title is displayed.
    expect(find.text('Collection Uploader V2 - xAI'), findsOneWidget);
    
    // Verify that configuration section exists.
    expect(find.text('⚙️ Configuração'), findsOneWidget);
  });
}
