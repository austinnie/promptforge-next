// apps/mobile/lib/services/ws_client.dart
import 'dart:async';

/// 后端 WebSocket 端点是「每个 job 一个连接」：
///     /api/v1/jobs/{job_id}/events
/// 没有全局 /ws 广播端点。
///
/// 现有 UI 用的是全局单连接，架构不匹配。为避免无意义的 403 重连刷屏，
/// 这里暂时把 WsClient 改成空实现；任务状态改用「创建后轮询 GET /jobs/{id}」。
///
/// 未来若要把 ws 用起来，请在 UI 层改成：针对每个 jobId 建立一条 ws 连接。
class WsClient {
  final String baseUrl;
  WsClient(this.baseUrl);

  final _events = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get events => _events.stream;

  final _connState = StreamController<bool>.broadcast();
  Stream<bool> get connectionState => _connState.stream;

  Future<void> connect() async {
    _connState.add(false);   // 不建立实际连接
  }

  Future<void> close() async {
    _connState.add(false);
  }

  void dispose() {
    _events.close();
    _connState.close();
  }
}