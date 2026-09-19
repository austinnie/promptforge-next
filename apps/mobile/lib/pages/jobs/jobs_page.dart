import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/task.dart';
import '../../services/connection_manager.dart';

class JobsPage extends StatefulWidget {
  const JobsPage({super.key});
  @override
  State<JobsPage> createState() => _JobsPageState();
}

class _JobsPageState extends State<JobsPage> {
  Timer? _timer;
  List<TaskItem> _tasks = [];
  bool _firstLoading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _refresh();
      _startPolling();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _refresh() async {
    final cm = context.read<ConnectionManager>();
    final list = await cm.api.listTasks(limit: 50);
    if (!mounted) return;
    setState(() {
      _tasks = list;
      _firstLoading = false;
    });
  }

  void _startPolling() {
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 2), (_) async {
      if (!mounted) return;
      // 只有当存在"未完成"任务时才轮询，省流量
      final hasRunning = _tasks.any((t) =>
          t.status == TaskStatus.pending || t.status == TaskStatus.running);
      if (!hasRunning && _tasks.isNotEmpty) return;
      await _refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: _firstLoading
          ? const Center(child: CircularProgressIndicator())
          : _tasks.isEmpty
              ? _buildEmpty()
              : ListView.separated(
                  padding: const EdgeInsets.all(12),
                  physics: const AlwaysScrollableScrollPhysics(),
                  itemCount: _tasks.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (ctx, i) => _TaskCard(
                    task: _tasks[i],
                    fileUrl: context.read<ConnectionManager>().api.fileUrl,
                    onTap: () => _showTaskDetail(_tasks[i]),
                  ),
                ),
    );
  }

  Widget _buildEmpty() {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 200),
        Icon(Icons.inbox_outlined, size: 64, color: Colors.grey.shade400),
        const SizedBox(height: 16),
        const Center(
          child: Text(
            '还没有任务\n去「生成」页提交一个试试',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey),
          ),
        ),
      ],
    );
  }

  void _showTaskDetail(TaskItem task) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => _TaskDetailSheet(
        task: task,
        fileUrl: context.read<ConnectionManager>().api.fileUrl,
      ),
    );
  }
}

// ============================================================
// 任务卡片
// ============================================================
class _TaskCard extends StatelessWidget {
  final TaskItem task;
  final String Function(String) fileUrl;
  final VoidCallback? onTap;

  const _TaskCard({required this.task, required this.fileUrl, this.onTap});

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

  Color _statusColor(TaskStatus s) {
    switch (s) {
      case TaskStatus.pending:
        return Colors.grey;
      case TaskStatus.running:
        return Colors.blue;
      case TaskStatus.success:
        return Colors.green;
      case TaskStatus.failed:
        return Colors.red;
      case TaskStatus.cancelled:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final showProgress =
        task.status == TaskStatus.pending || task.status == TaskStatus.running;
    final hasImage = task.status == TaskStatus.success &&
        task.resultUrl != null &&
        task.resultUrl!.isNotEmpty;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Card(
        elevation: 1,
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  // 缩略图
                  if (hasImage)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: Image.network(
                        fileUrl(task.resultUrl!),
                        width: 56,
                        height: 56,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          width: 56,
                          height: 56,
                          color: Colors.grey.shade200,
                          child: const Icon(Icons.broken_image, size: 20),
                        ),
                      ),
                    )
                  else
                    Container(
                      width: 56,
                      height: 56,
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Icon(
                        task.status == TaskStatus.failed
                            ? Icons.error_outline
                            : Icons.image_outlined,
                        color: Colors.grey,
                      ),
                    ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _statusLabel(task.status),
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: _statusColor(task.status),
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          task.prompt.isEmpty ? '(无描述)' : task.prompt,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 13),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          task.id,
                          style: TextStyle(
                            fontSize: 10,
                            color: Colors.grey.shade500,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: Colors.grey),
                ],
              ),
              if (showProgress) ...[
                const SizedBox(height: 10),
                LinearProgressIndicator(
                  value: task.progress > 0 ? task.progress : null,
                  minHeight: 4,
                ),
              ],
              if (task.status == TaskStatus.failed && task.error != null) ...[
                const SizedBox(height: 8),
                Text(
                  task.error!,
                  style: const TextStyle(color: Colors.red, fontSize: 12),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================
// 任务详情底部弹窗
// ============================================================
class _TaskDetailSheet extends StatelessWidget {
  final TaskItem task;
  final String Function(String) fileUrl;

  const _TaskDetailSheet({required this.task, required this.fileUrl});

  @override
  Widget build(BuildContext context) {
    final hasImage = task.status == TaskStatus.success &&
        task.resultUrl != null &&
        task.resultUrl!.isNotEmpty;

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Text('任务详情',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.pop(context),
                ),
              ],
            ),
            const Divider(height: 1),
            const SizedBox(height: 12),
            _kv('状态', task.status.name),
            _kv('进度', '${(task.progress * 100).toStringAsFixed(0)}%'),
            _kv('类型', task.type),
            _kv('描述', task.prompt.isEmpty ? '(无)' : task.prompt),
            _kv('创建时间', task.createdAt.toString().substring(0, 19)),
            _kv('任务 ID', task.id),
            if (task.error != null) _kv('错误', task.error!, isError: true),
            if (hasImage) ...[
              const SizedBox(height: 12),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.network(
                  fileUrl(task.resultUrl!),
                  fit: BoxFit.contain,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _kv(String k, String v, {bool isError = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 72,
            child: Text(k, style: const TextStyle(color: Colors.grey)),
          ),
          Expanded(
            child: Text(
              v,
              style: TextStyle(color: isError ? Colors.red : null),
            ),
          ),
        ],
      ),
    );
  }
}