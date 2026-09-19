import 'package:flutter/material.dart';
import '../models/task.dart';

class StatusBadge extends StatelessWidget {
  final TaskStatus status;
  const StatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    late final Color c;
    late final String t;
    switch (status) {
      case TaskStatus.pending:   c = Colors.grey;    t = '等待';
      case TaskStatus.running:   c = Colors.blue;    t = '执行';
      case TaskStatus.success:   c = Colors.green;   t = '成功';
      case TaskStatus.failed:    c = Colors.red;     t = '失败';
      case TaskStatus.cancelled: c = Colors.orange;  t = '取消';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
	  decoration: BoxDecoration(
	    color: c.withValues(alpha: 0.15),   // ← 改这里
	    borderRadius: BorderRadius.circular(12),
	  ),
      child: Text(t, style: TextStyle(color: c, fontWeight: FontWeight.w600)),
    );
  }
}