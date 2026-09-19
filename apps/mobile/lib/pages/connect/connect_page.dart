import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import '../../services/connection_manager.dart';

class ConnectPage extends StatefulWidget {
  const ConnectPage({super.key});
  @override
  State<ConnectPage> createState() => _ConnectPageState();
}

class _ConnectPageState extends State<ConnectPage> {
  late final TextEditingController _ctrl;
  bool _testing = false;
  String? _msg;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(
        text: context.read<ConnectionManager>().backendUrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  bool get _isMobile => !kIsWeb && (Platform.isAndroid || Platform.isIOS);

  Future<void> _apply() async {
    setState(() { _testing = true; _msg = null; });
    final cm = context.read<ConnectionManager>();
    final ok = await cm.setBackend(_ctrl.text);
    await cm.connectWs();
    await cm.refreshServerInfo();
    setState(() {
      _testing = false;
      _msg = ok ? '✅ 连接成功' : '❌ 无法连接后端';
    });
  }

  Future<void> _scan() async {
    final result = await Navigator.of(context).push<String>(
      MaterialPageRoute(builder: (_) => const _ScannerPage()),
    );
    if (result != null) {
      _ctrl.text = result;
      await _apply();
    }
  }

  @override
  Widget build(BuildContext context) {
    final cm = context.watch<ConnectionManager>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('后端地址',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                TextField(
                  controller: _ctrl,
                  decoration: const InputDecoration(
                    hintText: 'http://192.168.1.10:8000',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                Row(children: [
                  FilledButton.icon(
                    onPressed: _testing ? null : _apply,
                    icon: const Icon(Icons.link),
                    label: const Text('应用并连接'),
                  ),
                  const SizedBox(width: 8),
                  if (_isMobile)
                    OutlinedButton.icon(
                      onPressed: _scan,
                      icon: const Icon(Icons.qr_code_scanner),
                      label: const Text('扫码'),
                    ),
                ]),
                if (_msg != null) ...[
                  const SizedBox(height: 8),
                  Text(_msg!),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('状态', style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('当前地址：${cm.backendUrl}'),
                Text('WebSocket：${cm.wsOnline ? "在线" : "离线"}'),
                Text('服务端版本：${cm.serverVersion ?? "未知"}'),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        if (!_isMobile)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(children: [
                const Text('手机扫码连接',
                    style: TextStyle(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                SizedBox(
                  width: 220,
                  height: 220,
                  child: QrImageView(
                    data: cm.backendUrl,
                    version: QrVersions.auto,
                    backgroundColor: Colors.white,
                  ),
                ),
                const SizedBox(height: 8),
                const Text('手机 App 点「扫码」对准此二维码即可'),
              ]),
            ),
          ),
      ],
    );
  }
}

class _ScannerPage extends StatefulWidget {
  const _ScannerPage();
  @override
  State<_ScannerPage> createState() => _ScannerPageState();
}

class _ScannerPageState extends State<_ScannerPage> {
  final controller = MobileScannerController();
  bool _handled = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('扫码')),
      body: MobileScanner(
        controller: controller,
        onDetect: (capture) {
          if (_handled) return;
          final raw = capture.barcodes.first.rawValue;
          if (raw != null && raw.startsWith('http')) {
            _handled = true;
            controller.stop();
            Navigator.of(context).pop(raw);
          }
        },
      ),
    );
  }
}