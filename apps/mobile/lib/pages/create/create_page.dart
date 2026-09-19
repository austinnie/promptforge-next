import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/task.dart';
import '../../services/connection_manager.dart';

class CreatePage extends StatefulWidget {
  const CreatePage({super.key});
  @override
  State<CreatePage> createState() => _CreatePageState();
}

class _CreatePageState extends State<CreatePage> {
  final _promptCtrl = TextEditingController();
  final _presetCtrl = TextEditingController();
  int _width = 1024, _height = 1024;
  bool _busy = false;
  String? _msg;
  List<String> _presets = [];

  // === 轮询相关 ===
  Timer? _pollTimer;
  TaskItem? _currentTask;   // 当前正在跟踪的任务

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadPresets());
  }

  Future<void> _loadPresets() async {
    final cm = context.read<ConnectionManager>();
    final list = await cm.api.listPresets();
    if (mounted) setState(() => _presets = list);
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _promptCtrl.dispose();
    _presetCtrl.dispose();
    super.dispose();
  }

  // ============================================================
  // 提交
  // ============================================================
  Future<void> _submit() async {
    final cm = context.read<ConnectionManager>();
    final prompt = _promptCtrl.text.trim();
    final preset = _presetCtrl.text.trim();

    if (prompt.isEmpty && preset.isEmpty) {
      setState(() => _msg = '请输入描述或选择预设');
      return;
    }

    // 停掉上一个任务的轮询（用户可能连续提交）
    _pollTimer?.cancel();

    setState(() {
      _busy = true;
      _msg = null;
      _currentTask = null;
    });

    final params = <String, dynamic>{
      'width': _width,
      'height': _height,
      if (preset.isNotEmpty) 'preset': preset,
    };

    final task = await cm.api.createTask(
      type: preset.isNotEmpty ? 'preset' : 'text2img',
      prompt: prompt,
      params: params,
    );

    if (!mounted) return;

    if (task == null) {
      setState(() {
        _busy = false;
        _msg = '❌ 创建任务失败';
      });
      return;
    }

    setState(() {
      _busy = false;
      _msg = '✅ 已提交任务 ${task.id}，正在生成…';
      _currentTask = task;
    });
    _promptCtrl.clear();

    // 开始轮询
    _startPolling(task.id);
  }

  // ============================================================
  // 轮询
  // ============================================================
  void _startPolling(String jobId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (t) async {
      if (!mounted) {
        t.cancel();
        return;
      }

      final cm = context.read<ConnectionManager>();
      final latest = await cm.api.getTask(jobId);
      if (!mounted) {
        t.cancel();
        return;
      }

      if (latest == null) return;

      setState(() => _currentTask = latest);

      // 终态：停轮询
      if (latest.status == TaskStatus.success ||
          latest.status == TaskStatus.failed ||
          latest.status == TaskStatus.cancelled) {
        t.cancel();
        if (latest.status == TaskStatus.success) {
          setState(() => _msg = '🎉 生成完成');
        } else if (latest.status == TaskStatus.failed) {
          setState(() => _msg = '❌ 生成失败：${latest.error ?? "未知错误"}');
        } else {
          setState(() => _msg = '⏹️ 已取消');
        }
      }
    });
  }

  // ============================================================
  // UI
  // ============================================================
  @override
  Widget build(BuildContext context) {
    final cm = context.read<ConnectionManager>();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextField(
          controller: _promptCtrl,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: '描述',
            hintText: '例如：月光下的森林，镜头缓缓推进',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(
            child: TextField(
              controller: _presetCtrl,
              decoration: const InputDecoration(
                labelText: '预设（可选）',
                hintText: 'mecha_glow',
                border: OutlineInputBorder(),
              ),
            ),
          ),
          const SizedBox(width: 8),
          if (_presets.isNotEmpty)
            DropdownButton<String>(
              hint: const Text('选'),
              items: _presets
                  .take(200)
                  .map((p) => DropdownMenuItem(value: p, child: Text(p)))
                  .toList(),
              
			  onChanged: (v) {
			    if (v == null || v.isEmpty) return;
			    // "mecha_glow — 机甲发光" → "mecha_glow"
			    final name = v.contains(' — ')
			  	  ? v.split(' — ').first.trim()
			  	  : v.trim();
			    setState(() => _presetCtrl.text = name);
			  },			  
            ),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          const Text('尺寸：'),
          const SizedBox(width: 8),
          DropdownButton<int>(
            value: _width,
            items: const [512, 768, 1024, 1280, 1536]
                .map((v) => DropdownMenuItem(value: v, child: Text('$v')))
                .toList(),
            onChanged: (v) => setState(() => _width = v ?? 1024),
          ),
          const Text(' × '),
          DropdownButton<int>(
            value: _height,
            items: const [512, 768, 1024, 1280, 1536]
                .map((v) => DropdownMenuItem(value: v, child: Text('$v')))
                .toList(),
            onChanged: (v) => setState(() => _height = v ?? 1024),
          ),
        ]),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: _busy ? null : _submit,
          icon: _busy
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.send),
          label: Text(_busy ? '提交中…' : '提交生成'),
        ),

        if (_msg != null) ...[
          const SizedBox(height: 12),
          Text(
            _msg!,
            style: TextStyle(
              color: _msg!.startsWith('❌')
                  ? Colors.red
                  : _msg!.startsWith('🎉')
                      ? Colors.green
                      : null,
            ),
          ),
        ],

        // ===== 任务实时状态卡片 =====
        if (_currentTask != null) ...[
          const SizedBox(height: 20),
          _TaskStatusCard(
            task: _currentTask!,
            fileUrl: cm.api.fileUrl,
          ),
        ],
      ],
    );
  }
}

// ============================================================
// 任务状态卡片
// ============================================================
class _TaskStatusCard extends StatelessWidget {
  final TaskItem task;
  final String Function(String) fileUrl;

  const _TaskStatusCard({
    required this.task,
    required this.fileUrl,
  });

  String _statusLabel(TaskStatus s) {
    switch (s) {
      case TaskStatus.pending:
        return '⏳ 等待中';
      case TaskStatus.running:
        return '🎨 生成中';
      case TaskStatus.success:
        return '✅ 已完成';
      case TaskStatus.failed:
        return '❌ 失败';
      case TaskStatus.cancelled:
        return '⏹️ 已取消';
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDone = task.status == TaskStatus.success;
    final isFailed = task.status == TaskStatus.failed;

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 状态行
            Row(
              children: [
                Text(
                  _statusLabel(task.status),
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                ),
                const Spacer(),
                Text(
                  '${(task.progress * 100).toStringAsFixed(0)}%',
                  style: const TextStyle(color: Colors.grey),
                ),
              ],
            ),
            const SizedBox(height: 8),

            // 进度条
            LinearProgressIndicator(value: task.progress),
            const SizedBox(height: 12),

            // 图片（完成后显示）
            if (isDone && task.resultUrl != null && task.resultUrl!.isNotEmpty)
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(
                  fileUrl(task.resultUrl!),
                  fit: BoxFit.contain,
                  loadingBuilder: (ctx, child, progress) {
                    if (progress == null) return child;
                    return const SizedBox(
                      height: 200,
                      child: Center(child: CircularProgressIndicator()),
                    );
                  },
                  errorBuilder: (ctx, err, st) => Container(
                    height: 120,
                    alignment: Alignment.center,
                    color: Colors.red.shade50,
                    child: Text(
                      '图片加载失败\n${fileUrl(task.resultUrl!)}',
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.red, fontSize: 12),
                    ),
                  ),
                ),
              ),

            // 失败信息
            if (isFailed && task.error != null) ...[
              const SizedBox(height: 8),
              Text(
                task.error!,
                style: const TextStyle(color: Colors.red, fontSize: 13),
              ),
            ],

            const SizedBox(height: 8),
            SelectableText(
              'ID: ${task.id}',
              style: const TextStyle(fontSize: 11, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}