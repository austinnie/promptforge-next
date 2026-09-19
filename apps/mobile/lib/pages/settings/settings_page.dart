import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/connection_manager.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final cm = context.watch<ConnectionManager>();
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        const ListTile(
          leading: Icon(Icons.info_outline),
          title: Text('关于'),
          subtitle: Text('PromptForge Mobile · v0.1.0'),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.cloud_outlined),
          title: const Text('后端地址'),
          subtitle: Text(cm.backendUrl),
        ),
        ListTile(
          leading: Icon(
            cm.wsOnline ? Icons.check_circle : Icons.cancel,
            color: cm.wsOnline ? Colors.green : Colors.red,
          ),
          title: const Text('WebSocket 连接'),
          subtitle: Text(cm.wsOnline ? '在线' : '离线'),
        ),
        ListTile(
          leading: const Icon(Icons.dns_outlined),
          title: const Text('服务端版本'),
          subtitle: Text(cm.serverVersion ?? '未知'),
        ),
        const Divider(),
        const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Text(
            '安全提示\n'
            '· App 端不缓存任何 API Key\n'
            '· 所有 Key 均保存在后端 .env\n'
            '· 切换地址会自动重连 WebSocket',
            style: TextStyle(color: Colors.grey, fontSize: 13, height: 1.6),
          ),
        ),
      ],
    );
  }
}