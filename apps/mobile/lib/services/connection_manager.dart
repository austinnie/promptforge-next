import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/app_config.dart';
import 'api_client.dart';
import 'ws_client.dart';

class ConnectionManager extends ChangeNotifier {
  static const _kBackend = 'backend_url';

  late ApiClient api;
  late WsClient ws;

  String _backendUrl = '';
  bool _wsOnline = false;
  String? _serverVersion;

  String get backendUrl => _backendUrl;
  bool get wsOnline => _wsOnline;
  String? get serverVersion => _serverVersion;

  ConnectionManager() {
    _backendUrl = AppConfig.defaultBackend();
    api = ApiClient(_backendUrl);
    ws = WsClient(_backendUrl);
  }

  Future<void> bootstrap() async {
    final sp = await SharedPreferences.getInstance();
    final saved = sp.getString(_kBackend);
    if (saved != null && saved.isNotEmpty) {
      await setBackend(saved, persist: false);
    }
    await connectWs();
  }

  /// 切换后端地址；WS 一并重连（App 端不缓存任何 API Key）
  Future<bool> setBackend(String url, {bool persist = true}) async {
    final normalized = url.trim().replaceAll(RegExp(r'/+$'), '');
    if (normalized.isEmpty) return false;

    _backendUrl = normalized;
    api.baseUrl = normalized;

    // 地址变了 → WS 必须重连
    await ws.close();
    ws.dispose();
    ws = WsClient(normalized);
    _listenWs();

    if (persist) {
      final sp = await SharedPreferences.getInstance();
      await sp.setString(_kBackend, normalized);
    }

    notifyListeners();
    return await api.ping();
  }

  Future<void> connectWs() async {
    _listenWs();
    await ws.connect();
  }

  void _listenWs() {
    ws.connectionState.listen((online) {
      _wsOnline = online;
      notifyListeners();
    });
  }

  Future<void> refreshServerInfo() async {
    final info = await api.systemInfo();
    _serverVersion = info?['version']?.toString();
    notifyListeners();
  }

  @override
  void dispose() {
    ws.dispose();
    super.dispose();
  }
}