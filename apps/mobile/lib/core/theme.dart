import 'package:flutter/material.dart';

class AppTheme {
  static const Color seed = Color(0xFFC25B3B);

  static ThemeData light() => ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: seed),
        useMaterial3: true,
      );
}