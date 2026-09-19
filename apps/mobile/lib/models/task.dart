enum TaskStatus { pending, running, success, failed, cancelled }

TaskStatus parseTaskStatus(String? s) {
  switch (s) {
    case 'pending':   return TaskStatus.pending;
    case 'running':   return TaskStatus.running;
    case 'success':   return TaskStatus.success;
    case 'failed':    return TaskStatus.failed;
    case 'cancelled': return TaskStatus.cancelled;
    default:          return TaskStatus.pending;
  }
}

class TaskItem {
  final String id;
  final String type;          // text2img / img2img / video / preset
  final String prompt;
  final TaskStatus status;
  final double progress;      // 0.0 ~ 1.0
  final String? resultUrl;
  final String? error;
  final DateTime createdAt;

  TaskItem({
    required this.id,
    required this.type,
    required this.prompt,
    required this.status,
    required this.progress,
    this.resultUrl,
    this.error,
    required this.createdAt,
  });

  factory TaskItem.fromJson(Map<String, dynamic> j) => TaskItem(
        id: j['id'] as String,
        type: j['type'] as String? ?? 'text2img',
        prompt: j['prompt'] as String? ?? '',
        status: parseTaskStatus(j['status'] as String?),
        progress: (j['progress'] as num?)?.toDouble() ?? 0.0,
        resultUrl: j['result_url'] as String?,
        error: j['error'] as String?,
        createdAt: DateTime.tryParse(j['created_at'] as String? ?? '') ??
            DateTime.now(),
      );
}