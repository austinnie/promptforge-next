// apps/mobile/lib/services/skills_api.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

/// Skills API 客户端：列出 skill / 执行 action。
class SkillsApi {
  final String baseUrl;

  SkillsApi(this.baseUrl);

  String get _prefix => '$baseUrl/api/v1';

  /// 列出所有 skills（含 actions 元数据）。
  Future<List<Map<String, dynamic>>> listSkills() async {
    final r = await http.get(Uri.parse('$_prefix/skills'));
    if (r.statusCode != 200) {
      throw Exception('listSkills 失败: ${r.statusCode}');
    }
    final data = jsonDecode(utf8.decode(r.bodyBytes)) as List;
    return data.cast<Map<String, dynamic>>();
  }

  /// 执行 skill action。
  Future<Map<String, dynamic>> execute(
    String skillName,
    String action, {
    Map<String, dynamic> params = const {},
  }) async {
    final r = await http.post(
      Uri.parse('$_prefix/skills/$skillName/execute'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'action': action, 'params': params}),
    );
    final body = jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
    if (r.statusCode != 200) {
      throw Exception(body['detail'] ?? 'execute 失败: ${r.statusCode}');
    }
    return body;
  }
}