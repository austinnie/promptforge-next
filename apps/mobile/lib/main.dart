import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'app.dart';
import 'services/connection_manager.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final cm = ConnectionManager();
  await cm.bootstrap();
  runApp(
    ChangeNotifierProvider.value(
      value: cm,
      child: const PromptForgeApp(),
    ),
  );
}