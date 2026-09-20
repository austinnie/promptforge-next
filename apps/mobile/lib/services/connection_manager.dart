import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/app_config.dart';
import 'api_client.dart';
import 'ws_client.dart';

class ConnectionManager extends ChangeNotifier {
  static const _kBackend = 'backend_url';
  static const _pingInterval = Duration(seconds: 10);

  late ApiClient api;
  late WsClient ws;

  String _backendUrl = '';
  bool _wsOnline = false;
  bool _httpOnline = false;
  String? _serverVersion;
  Timer? _pingTimer;

  String get backendUrl => _backendUrl;
  bool get wsOnline => _wsOnline;

  /// HTTP 是否通（顶部指示灯用这个）
  bool get httpOnline => _httpOnline;

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

    // 立刻 ping 一次 + 起定时器
    await _pingOnce();
    _startPingTimer();
  }

  /// 切换后端地址；WS 一并重连
  Future<bool> setBackend(String url, {bool persist = true}) async {
    final normalized = url.trim().replaceAll(RegExp(r'/+$'), '');
    if (normalized.isEmpty) return false;

    _backendUrl = normalized;
    api.baseUrl = normalized;

    await ws.close();
    ws.dispose();
    ws = WsClient(normalized);
    _listenWs();

    if (persist) {
      final sp = await SharedPreferences.getInstance();
      await sp.setString(_kBackend, normalized);
    }

    notifyListeners();

    // 连接后立刻 ping，给界面即时反馈
    final ok = await _pingOnce();

    // 保证 ping 定时器在跑
    if (_pingTimer == null || !_pingTimer!.isActive) {
      _startPingTimer();
    }

    return ok;
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

  Future<bool> _pingOnce() async {
    final ok = await api.ping();
    if (_httpOnline != ok) {
      _httpOnline = ok;
      notifyListeners();
    }
    return ok;
  }

  void _startPingTimer() {
    _pingTimer?.cancel();
    _pingTimer = Timer.periodic(_pingInterval, (_) {
      _pingOnce();
    });
  }

  Future<void> refreshServerInfo() async {
    final info = await api.systemInfo();
    _serverVersion = info?['version']?.toString();
    notifyListeners();
  }

  @override
  void dispose() {
    _pingTimer?.cancel();
    ws.dispose();
    super.dispose();
  }
}