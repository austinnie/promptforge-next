import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../models/task.dart';
import '../../services/connection_manager.dart';
import '../../widgets/status_badge.dart';

class JobsPage extends StatefulWidget {
  const JobsPage({super.key});
  @override
  State<JobsPage> createState() => _JobsPageState();
}

class _JobsPageState extends State<JobsPage> {
  List<TaskItem> _tasks = [];
  StreamSubscription? _sub;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _listen();
      _refresh();
    });
  }

  void _listen() {
    final cm = context.read<ConnectionManager>();
    _sub = cm.ws.events.listen((event) {
      if (event['type'] == 'task_update' && event['task'] != null) {
        final updated =
            TaskItem.fromJson((event['task'] as Map).cast<String, dynamic>());
        if (!mounted) return;
        setState(() {
          final i = _tasks.indexWhere((t) => t.id == updated.id);
          if (i >= 0) {
            _tasks[i] = updated;
          } else {
            _tasks.insert(0, updated);
          }
        });
      }
    });
  }

  Future<void> _refresh() async {
    setState(() => _loading = true);
    final cm = context.read<ConnectionManager>();
    final list = await cm.api.listTasks();
    if (!mounted) return;
    setState(() { _tasks = list; _loading = false; });
  }

  Future<void> _cancel(TaskItem t) async {
    final cm = context.read<ConnectionManager>();
    final ok = await cm.api.cancelTask(t.id);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(ok ? '已请求取消' : '取消失败')),
    );
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_tasks.isEmpty) {
      return RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(children: const [
          SizedBox(height: 200),
          Center(child: Text('暂无任务')),
        ]),
      );
    }
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView.builder(
        itemCount: _tasks.length,
        itemBuilder: (_, i) {
          final t = _tasks[i];
          return Card(
            margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            child: ListTile(
              title: Text(t.prompt.isEmpty ? t.type : t.prompt,
                  maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${t.type} · ${t.id.substring(0, 8)}'),
                  if (t.status == TaskStatus.running)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: LinearProgressIndicator(value: t.progress),
                    ),
                  if (t.error != null)
                    Text(t.error!,
                        style:
                            const TextStyle(color: Colors.red, fontSize: 12)),
                ],
              ),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  StatusBadge(status: t.status),
                  if (t.status == TaskStatus.pending ||
                      t.status == TaskStatus.running)
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => _cancel(t),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}