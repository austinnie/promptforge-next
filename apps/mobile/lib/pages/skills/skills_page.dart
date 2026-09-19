// apps/mobile/lib/pages/skills/skills_page.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/connection_manager.dart';
import '../../services/skills_api.dart';

class SkillsPage extends StatefulWidget {
  const SkillsPage({super.key});

  @override
  State<SkillsPage> createState() => _SkillsPageState();
}

class _SkillsPageState extends State<SkillsPage> {
  SkillsApi? _api;
  String _baseUrl = '';

  List<Map<String, dynamic>> _skills = [];
  Map<String, dynamic>? _currentSkill;
  Map<String, dynamic>? _currentAction;

  bool _loading = true;
  bool _running = false;
  String? _error;

  final Map<String, dynamic> _formValues = {};
  Map<String, dynamic>? _lastResult;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final cm = context.watch<ConnectionManager>();
    final baseUrl = cm.api.baseUrl;

    // baseUrl 变化（首次连接/重连）时重建 api 并刷新
    if (baseUrl.isNotEmpty && baseUrl != _baseUrl) {
      _baseUrl = baseUrl;
      _api = SkillsApi(baseUrl);
      _loadSkills();
    }
  }

  // ==================== 数据加载 ====================

  Future<void> _loadSkills() async {
    final api = _api;
    if (api == null) return;

    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final skills = await api.listSkills();     // ← 用局部 api
      if (!mounted) return;
      setState(() {
        _skills = skills;
        _loading = false;
        if (skills.isNotEmpty) {
          _selectSkill(skills.first);
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loading = false;
        _error = e.toString();
      });
    }
  }

  void _selectSkill(Map<String, dynamic> skill) {
    final actions = (skill['actions'] as List?) ?? const [];
    _currentSkill = skill;
    if (actions.isEmpty) {
      _currentAction = null;
      return;
    }
    _selectAction(skill, actions.first);
  }

  void _selectAction(Map<String, dynamic> skill, Map<String, dynamic> action) {
    _currentAction = action;
    _formValues.clear();
    _lastResult = null;

    final params = (action['params'] as List?) ?? const [];
    for (final p in params) {
      final name = p['name'] as String;
      _formValues[name] = p['default'] ?? _defaultForType(p['type']);
    }
  }

  dynamic _defaultForType(String? type) {
    switch (type) {
      case 'boolean':
        return false;
      case 'integer':
      case 'number':
        return 0;
      default:
        return '';
    }
  }

  // ==================== 执行 ====================

  Future<void> _execute() async {
    final api = _api;
    if (api == null || _currentSkill == null || _currentAction == null) {
      return;
    }
    setState(() {
      _running = true;
      _error = null;
      _lastResult = null;
    });
    try {
      final result = await api.execute(          // ← 用局部 api
        _currentSkill!['id'] as String,
        _currentAction!['id'] as String,
        params: Map<String, dynamic>.from(_formValues),
      );
      if (!mounted) return;
      setState(() {
        _lastResult = result;
        _running = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _running = false;
      });
    }
  }

  Future<void> _openUrl(String path) async {
    final full = path.startsWith('http') ? path : '$_baseUrl$path';
    final uri = Uri.parse(full);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('无法打开: $full')),
      );
    }
  }

  // ==================== 构建 ====================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('技能'),
        actions: [
          IconButton(
            tooltip: '刷新',
            icon: const Icon(Icons.refresh),
            onPressed: _loading ? null : _loadSkills,
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _skills.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 48, color: Colors.red),
              const SizedBox(height: 12),
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadSkills,
                child: const Text('重试'),
              ),
            ],
          ),
        ),
      );
    }
    if (_skills.isEmpty) {
      return const Center(child: Text('没有可用技能'));
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildSkillSelector(),
        const SizedBox(height: 16),
        if (_currentSkill != null) _buildActionSelector(),
        const SizedBox(height: 16),
        if (_currentAction != null) _buildParamForm(),
        const SizedBox(height: 16),
        _buildExecuteButton(),
        const SizedBox(height: 24),
        if (_error != null) _buildError(),
        if (_lastResult != null) _buildResult(),
      ],
    );
  }

  Widget _buildSkillSelector() {
    return DropdownButtonFormField<String>(
      initialValue: _currentSkill?['id'] as String?,
      decoration: const InputDecoration(
        labelText: '技能',
        border: OutlineInputBorder(),
      ),
      isExpanded: true,
      items: _skills
          .map<DropdownMenuItem<String>>((s) => DropdownMenuItem(
                value: s['id'] as String,
                child: Text('${s['name']}  (${s['id']})'),
              ))
          .toList(),
      onChanged: (id) {
        if (id == null) return;
        final s = _skills.firstWhere((x) => x['id'] == id);
        setState(() => _selectSkill(s));
      },
    );
  }

  Widget _buildActionSelector() {
    final actions = (_currentSkill!['actions'] as List?) ?? const [];
    return DropdownButtonFormField<String>(
      initialValue: _currentAction?['id'] as String?,
      decoration: const InputDecoration(
        labelText: '操作',
        border: OutlineInputBorder(),
      ),
      isExpanded: true,
      items: actions
          .map<DropdownMenuItem<String>>((a) => DropdownMenuItem(
                value: a['id'] as String,
                child: Text('${a['name']}  (${a['id']})'),
              ))
          .toList(),
      onChanged: (id) {
        if (id == null) return;
        final a = actions.firstWhere((x) => x['id'] == id);
        setState(() => _selectAction(_currentSkill!, a));
      },
    );
  }

  Widget _buildParamForm() {
    final params = (_currentAction!['params'] as List?) ?? const [];
    if (params.isEmpty) {
      return const Text('（此操作无参数）');
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: params.map<Widget>((p) => _buildParamField(p)).toList(),
    );
  }

  Widget _buildParamField(Map<String, dynamic> p) {
    final name = p['name'] as String;
    final type = (p['type'] ?? 'string') as String;
    final label = (p['description'] as String?) ?? name;

    if (type == 'boolean') {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: SwitchListTile(
          title: Text(label),
          subtitle: Text(name),
          value: (_formValues[name] as bool?) ?? false,
          onChanged: (v) => setState(() => _formValues[name] = v),
          contentPadding: EdgeInsets.zero,
        ),
      );
    }

    final isNumber = type == 'integer' || type == 'number';
    final isLongText = name == 'text' || name == 'text_file';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: TextFormField(
        initialValue: _formValues[name]?.toString() ?? '',
        decoration: InputDecoration(
          labelText: label,
          helperText: name,
          border: const OutlineInputBorder(),
        ),
        keyboardType: isNumber ? TextInputType.number : TextInputType.text,
        maxLines: isLongText ? 5 : 1,
        onChanged: (v) {
          if (isNumber) {
            _formValues[name] = type == 'integer'
                ? (int.tryParse(v) ?? 0)
                : (double.tryParse(v) ?? 0);
          } else {
            _formValues[name] = v;
          }
        },
      ),
    );
  }

  Widget _buildExecuteButton() {
    return SizedBox(
      height: 48,
      child: ElevatedButton.icon(
        onPressed: _running ? null : _execute,
        icon: _running
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : const Icon(Icons.play_arrow),
        label: Text(_running ? '执行中…' : '执行'),
      ),
    );
  }

  Widget _buildError() {
    return Card(
      color: Colors.red.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            const Icon(Icons.error_outline, color: Colors.red),
            const SizedBox(width: 8),
            Expanded(child: Text(_error!)),
          ],
        ),
      ),
    );
  }

  Widget _buildResult() {
    final res = _lastResult!;
    final status = res['status'] ?? 'unknown';
    final result = res['result'] as Map<String, dynamic>?;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  status == 'success' ? Icons.check_circle : Icons.error,
                  color: status == 'success' ? Colors.green : Colors.red,
                ),
                const SizedBox(width: 8),
                Text(
                  '状态: $status',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            if (result != null) ...[
              const SizedBox(height: 12),
              ..._buildResultItems(result),
            ],
          ],
        ),
      ),
    );
  }

  List<Widget> _buildResultItems(Map<String, dynamic> result) {
    final widgets = <Widget>[];

    for (final key in ['audio_path', 'midi_path', 'lyrics_path']) {
      final v = result[key];
      if (v is String && v.isNotEmpty) {
        widgets.add(_linkRow(key, v));
      }
    }

    final paths = result['audio_paths'];
    if (paths is List && paths.isNotEmpty) {
      widgets.add(const SizedBox(height: 4));
      widgets.add(Text('共 ${paths.length} 段'));
      for (var i = 0; i < paths.length && i < 5; i++) {
        widgets.add(_linkRow('音频 ${i + 1}', paths[i].toString()));
      }
      if (paths.length > 5) {
        widgets.add(Text('… 还有 ${paths.length - 5} 段'));
      }
    }

    final lyrics = result['lyrics'];
    if (lyrics is Map) {
      final title = lyrics['title'];
      if (title != null) {
        widgets.add(const SizedBox(height: 8));
        widgets.add(Text(
          '歌词标题: $title',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ));
      }
      final structure = lyrics['structure'];
      if (structure is Map) {
        structure.forEach((k, v) {
          if (v is List && v.isNotEmpty) {
            widgets.add(const SizedBox(height: 4));
            widgets.add(Text(
              '[$k]',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ));
            for (final line in v) {
              widgets.add(Text('  $line'));
            }
          }
        });
      }
    }

    if (widgets.isEmpty) {
      result.forEach((k, v) {
        if (v is String || v is num || v is bool) {
          widgets.add(Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Text('$k: $v'),
          ));
        }
      });
    }

    return widgets;
  }

  Widget _linkRow(String label, String path) {
    final isMidi = path.toLowerCase().endsWith('.mid') ||
        path.toLowerCase().endsWith('.midi');
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(
            isMidi ? Icons.music_note : Icons.audiotrack,
            color: isMidi ? Colors.deepPurple : Colors.blue,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              '$label: $path',
              style: const TextStyle(fontSize: 13),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          TextButton(
            onPressed: () => _openUrl(path),
            child: const Text('打开'),
          ),
        ],
      ),
    );
  }
}