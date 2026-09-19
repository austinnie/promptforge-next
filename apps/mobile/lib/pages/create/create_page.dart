import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
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
    _promptCtrl.dispose();
    _presetCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final cm = context.read<ConnectionManager>();
    final prompt = _promptCtrl.text.trim();
    final preset = _presetCtrl.text.trim();

    if (prompt.isEmpty && preset.isEmpty) {
      setState(() => _msg = '请输入描述或选择预设');
      return;
    }

    setState(() { _busy = true; _msg = null; });

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
    setState(() {
      _busy = false;
      _msg = task == null ? '❌ 创建任务失败' : '✅ 已提交任务 ${task.id}';
    });
    if (task != null) _promptCtrl.clear();
  }

  @override
  Widget build(BuildContext context) {
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
              onChanged: (v) => setState(() => _presetCtrl.text = v ?? ''),
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
          Text(_msg!),
        ],
      ],
    );
  }
}