class WorkItem {
  final String id;
  final String url;
  final String? prompt;
  final DateTime createdAt;

  WorkItem({
    required this.id,
    required this.url,
    this.prompt,
    required this.createdAt,
  });

  factory WorkItem.fromJson(Map<String, dynamic> j) {
    // id: 兼容 id / job_id
    final id = (j['id'] ?? j['job_id'] ?? '') as String;

    // url: 优先顶层 url，其次 result 里的各种可能字段
    String url = (j['url'] as String?) ?? '';
    if (url.isEmpty && j['result'] is Map) {
      final r = j['result'] as Map;
      url = (r['url'] ??
              r['image_url'] ??
              r['file_url'] ??
              r['path'] ??
              r['key'] ??
              '')
          as String;
    }
    // 如果是相对路径（如 /files/xxx.png 或 xxx.png），交给 ApiClient.fileUrl 拼
    // 这里不做处理，由上层用 ApiClient.fileUrl(work.url) 拼全

    final prompt = (j['prompt'] as String?) ?? (j['message'] as String?) ?? null;

    return WorkItem(
      id: id,
      url: url,
      prompt: prompt,
      createdAt: DateTime.tryParse(j['created_at'] as String? ?? '') ??
          DateTime.now(),
    );
  }
}