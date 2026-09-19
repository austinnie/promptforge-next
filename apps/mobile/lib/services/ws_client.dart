import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../core/app_config.dart';

class WsClient {
  final String baseUrl;
  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _pingTimer;
  bool _closedByUser = false;

  final _events = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get events => _events.stream;

  final _connState = StreamController<bool>.broadcast();
  Stream<bool> get connectionState => _connState.stream;

  WsClient(this.baseUrl);

  Future<void> connect() async {
    _closedByUser = false;
    await _open();
  }

  Future<void> _open() async {
    try {
      final uri = Uri.parse('${baseUrl.replaceFirst('http', 'ws')}/ws');
      _channel = WebSocketChannel.connect(uri);
      await _channel!.ready;
      _connState.add(true);

      _sub = _channel!.stream.listen(
        (data) {
          try {
            final obj = jsonDecode(data as String) as Map<String, dynamic>;
            _events.add(obj);
          } catch (_) {}
        },
        onError: (_) => _scheduleReconnect(),
        onDone: () => _scheduleReconnect(),
        cancelOnError: true,
      );

      _pingTimer?.cancel();
      _pingTimer = Timer.periodic(AppConfig.wsPingInterval, (_) {
        try {
          _channel?.sink.add(jsonEncode({'type': 'ping'}));
        } catch (_) {}
      });
    } catch (_) {
      _connState.add(false);
      _scheduleReconnect();
    }
  }

  void _scheduleReconnect() {
    if (_closedByUser) return;
    _connState.add(false);
    _pingTimer?.cancel();
    _sub?.cancel();
    Future.delayed(AppConfig.wsReconnectDelay, () {
      if (!_closedByUser) _open();
    });
  }

  Future<void> close() async {
    _closedByUser = true;
    _pingTimer?.cancel();
    await _sub?.cancel();
    await _channel?.sink.close();
    _channel = null;
    _connState.add(false);
  }

  void dispose() {
    close();
    _events.close();
    _connState.close();
  }
}