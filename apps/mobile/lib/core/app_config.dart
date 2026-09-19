import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

class AppConfig {
  /// 默认后端地址：桌面端 localhost，移动端让用户改
  static String defaultBackend() {
    if (kIsWeb) return 'http://localhost:8000';
    if (Platform.isAndroid || Platform.isIOS) {
      return 'http://192.168.1.100:8000';
    }
    return 'http://localhost:8000';
  }

  static const Duration httpTimeout = Duration(seconds: 30);
  static const Duration wsPingInterval = Duration(seconds: 20);
  static const Duration wsReconnectDelay = Duration(seconds: 3);
}	