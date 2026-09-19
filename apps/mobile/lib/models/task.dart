enum TaskStatus { pending, running, success, failed, cancelled }

TaskStatus parseTaskStatus(String? s) {
  switch (s) {
    case 'pending':
    case 'queued':
      return TaskStatus.pending;
    case 'running':
    case 'processing':
      return TaskStatus.running;
    case 'success':
    case 'succeeded':
    case 'done':
    case 'completed':
      return TaskStatus.success;
    case 'failed':
    case 'error':
      return TaskStatus.failed;
    case 'cancelled':
    case 'canceled':
      return TaskStatus.cancelled;
    default:
      return TaskStatus.pending;
  }
}

class TaskItem {
  final String id;
  final String type;          // text2img / img2img
  final String prompt;
  final TaskStatus status;
  final double progress;      // 统一 0.0 ~ 1.0
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

  factory TaskItem.fromJson(Map<String, dynamic> j) {
    // 1) progress: 兼容 0~100 的 int 与 0.0~1.0 的 double
    double raw = (j['progress'] as num?)?.toDouble() ?? 0.0;
    if (raw > 1.0) raw = raw / 100.0;

    // 2) result_url: 后端在 j['result'] 字典里
    String? resultUrl = j['result_url'] as String?;
    if (resultUrl == null && j['result'] is Map) {
      final r = j['result'] as Map;
      resultUrl = (r['url'] ?? r['image_url'] ?? r['file_url'] ?? r['path'])
          as String?;
    }

    // 3) prompt: 后端 Job 没这个字段，退化到 message
    final prompt = (j['prompt'] as String?) ?? (j['message'] as String?) ?? '';

    // 4) type: 后端 "image" → 前端 "text2img"
    var type = (j['type'] as String?) ?? 'text2img';
    if (type == 'image') type = 'text2img';

    return TaskItem(
      id: (j['id'] ?? j['job_id']) as String,
      type: type,
      prompt: prompt,
      status: parseTaskStatus(j['status'] as String?),
      progress: raw,
      resultUrl: resultUrl,
      error: j['error'] as String?,
      createdAt: DateTime.tryParse(j['created_at'] as String? ?? '') ??
          DateTime.now(),
    );
  }
}