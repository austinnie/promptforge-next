// apps/mobile/lib/pages/home/home_page.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../services/connection_manager.dart';
import '../connect/connect_page.dart';
import '../create/create_page.dart';
import '../jobs/jobs_page.dart';
import '../assets/assets_page.dart';
import '../skills/skills_page.dart';
import '../settings/settings_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _index = 0;

  // ⚠️ 从 static const 改为普通字段
  // 因为 SkillsPage 会通过 Provider 自己拿 baseUrl，但列表本身不再 const
  static const _pages = <Widget>[
    CreatePage(),
    JobsPage(),
    AssetsPage(),
    SkillsPage(),
    ConnectPage(),
    SettingsPage(),
  ];

  @override
  Widget build(BuildContext context) {
    final cm = context.watch<ConnectionManager>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('PromptForge'),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: Row(children: [
              Icon(
                Icons.circle,
                size: 10,
                color: cm.httpOnline ? Colors.green : Colors.red,
              ),
              const SizedBox(width: 6),
              Text(
                cm.httpOnline ? '在线' : '离线',
                style: const TextStyle(fontSize: 12),
              ),
            ]),
          ),
        ],
      ),
      body: IndexedStack(index: _index, children: _pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.auto_awesome),
            label: '生成',
          ),
          NavigationDestination(
            icon: Icon(Icons.list_alt),
            label: '任务',
          ),
          NavigationDestination(
            icon: Icon(Icons.photo_library),
            label: '作品',
          ),
          NavigationDestination(
            icon: Icon(Icons.auto_fix_high),   // ← 新 tab
            label: '技能',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_ethernet),
            label: '连接',
          ),
          NavigationDestination(
            icon: Icon(Icons.tune),
            label: '设置',
          ),
        ],
      ),
    );
  }
}