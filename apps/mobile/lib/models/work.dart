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

  factory WorkItem.fromJson(Map<String, dynamic> j) => WorkItem(
        id: j['id'] as String,
        url: j['url'] as String,
        prompt: j['prompt'] as String?,
        createdAt: DateTime.tryParse(j['created_at'] as String? ?? '') ??
            DateTime.now(),
      );
}