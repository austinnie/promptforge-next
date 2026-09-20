import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../../models/task.dart';
import '../../services/connection_manager.dart';

/// 生成模式
enum _CreateMode { text2img, img2img }

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

  // 模式
  _CreateMode _mode = _CreateMode.text2img;

  // 图生图参考图
  Uint8List? _refImageBytes;
  String? _refImageName;
  double _strength = 0.7;

  // 轮询
  Timer? _pollTimer;
  TaskItem? _currentTask;

  final _picker = ImagePicker();

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

  // ============ 参考图 ============

  Future<void> _pickReference() async {
    try {
      final x = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1536,
        maxHeight: 1536,
        imageQuality: 90,
      );
      if (x == null) return;
      final bytes = await x.readAsBytes();
      if (!mounted) return;
      setState(() {
        _refImageBytes = bytes;
        _refImageName = x.name;
        _msg = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _msg = '❌ 选择图片失败: $e');
    }
  }

  void _clearReference() {
    setState(() {
      _refImageBytes = null;
      _refImageName = null;
    });
  }

  // ============ 提交 ============

  Future<void> _submit() async {
    final cm = context.read<ConnectionManager>();
    final prompt = _promptCtrl.text.trim();
    final preset = _presetCtrl.text.trim();

    // 校验
    if (_mode == _CreateMode.text2img) {
      if (prompt.isEmpty && preset.isEmpty) {
        setState(() => _msg = '请输入描述或选择预设');
        return;
      }
    } else {
      if (prompt.isEmpty) {
        setState(() => _msg = '图生图需要输入描述');
        return;
      }
      if (_refImageBytes == null) {
        setState(() => _msg = '请先选择参考图');
        return;
      }
    }

    _pollTimer?.cancel();
    setState(() {
      _busy = true;
      _msg = null;
      _currentTask = null;
    });

    TaskItem? task;
    if (_mode == _CreateMode.text2img) {
      task = await cm.api.createTask(
        type: preset.isNotEmpty ? 'preset' : 'text2img',
        prompt: prompt,
        params: {
          'width': _width,
          'height': _height,
          if (preset.isNotEmpty) 'preset': preset,
        },
      );
    } else {
      task = await cm.api.createImageToImageTask(
        prompt: prompt,
        imageBytes: _refImageBytes!,
        strength: _strength,
        width: _width,
        height: _height,
      );
    }

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
      _msg = '✅ 已提交任务 ${task!.id}，正在生成…';
      _currentTask = task;
    });
    _promptCtrl.clear();

    _startPolling(task.id);
  }

  // ============ 轮询 ============

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

  // ============ UI ============

  @override
  Widget build(BuildContext context) {
    final cm = context.read<ConnectionManager>();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // ---- 模式切换 ----
        SegmentedButton<_CreateMode>(
          segments: const [
            ButtonSegment(
              value: _CreateMode.text2img,
              icon: Icon(Icons.text_fields),
              label: Text('文生图'),
            ),
            ButtonSegment(
              value: _CreateMode.img2img,
              icon: Icon(Icons.image),
              label: Text('图生图'),
            ),
          ],
          selected: {_mode},
          onSelectionChanged: (s) {
            setState(() {
              _mode = s.first;
              _msg = null;
            });
          },
        ),

        const SizedBox(height: 16),

        // ---- 参考图（仅图生图模式）----
        if (_mode == _CreateMode.img2img) ...[
          _ReferenceCard(
            bytes: _refImageBytes,
            name: _refImageName,
            onPick: _pickReference,
            onClear: _clearReference,
          ),
          const SizedBox(height: 12),
          Row(children: [
            const Text('修改强度：'),
            Expanded(
              child: Slider(
                value: _strength,
                min: 0.1,
                max: 1.0,
                divisions: 18,
                label: _strength.toStringAsFixed(2),
                onChanged: (v) => setState(() => _strength = v),
              ),
            ),
            Text(_strength.toStringAsFixed(2)),
          ]),
          const SizedBox(height: 12),
        ],

        // ---- 描述 ----
        TextField(
          controller: _promptCtrl,
          maxLines: 3,
          decoration: InputDecoration(
            labelText: '描述',
            hintText: _mode == _CreateMode.text2img
                ? '例如：月光下的森林，镜头缓缓推进'
                : '例如：改成梵高油画风格，星空旋转',
            border: const OutlineInputBorder(),
          ),
        ),

        const SizedBox(height: 12),

        // ---- 预设（文生图模式下可用）----
        if (_mode == _CreateMode.text2img)
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
                isExpanded: false,
                menuWidth: 380,
                menuMaxHeight: 480,
                items: _presets
                    .take(500)
                    .map((p) => DropdownMenuItem(
                          value: p,
                          child: Text(
                            p,
                            overflow: TextOverflow.ellipsis,
                            maxLines: 1,
                            style: const TextStyle(fontSize: 13),
                          ),
                        ))
                    .toList(),
                onChanged: (v) {
                  if (v == null || v.isEmpty) return;
                  var s = v.trim();
                  if (s.startsWith('[')) {
                    final end = s.indexOf(']');
                    if (end > 0) s = s.substring(end + 1).trim();
                  }
                  if (s.contains(' — ')) {
                    s = s.split(' — ').first.trim();
                  }
                  setState(() => _presetCtrl.text = s);
                },
              ),
          ]),

        const SizedBox(height: 12),

        // ---- 尺寸 ----
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
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
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
// 参考图卡片
// ============================================================
class _ReferenceCard extends StatelessWidget {
  final Uint8List? bytes;
  final String? name;
  final VoidCallback onPick;
  final VoidCallback onClear;

  const _ReferenceCard({
    required this.bytes,
    required this.name,
    required this.onPick,
    required this.onClear,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: bytes == null
            ? Row(
                children: [
                  const Icon(Icons.image_outlined, color: Colors.grey),
                  const SizedBox(width: 8),
                  const Expanded(child: Text('选择参考图（用于图生图）')),
                  FilledButton.tonal(
                    onPressed: onPick,
                    child: const Text('选择'),
                  ),
                ],
              )
            : Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: Image.memory(
                      bytes!,
                      width: 80,
                      height: 80,
                      fit: BoxFit.cover,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          name ?? '参考图',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                          overflow: TextOverflow.ellipsis,
                          maxLines: 1,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          '${(bytes!.lengthInBytes / 1024).toStringAsFixed(1)} KB',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.grey,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            TextButton(
                              onPressed: onPick,
                              child: const Text('换一张'),
                            ),
                            TextButton(
                              onPressed: onClear,
                              child: const Text('清除'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
      ),
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
            LinearProgressIndicator(value: task.progress),
            const SizedBox(height: 12),

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