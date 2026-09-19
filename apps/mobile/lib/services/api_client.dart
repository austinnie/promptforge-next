import 'dart:convert';
import 'package:http/http.dart' as http;
import '../core/app_config.dart';
import '../models/task.dart';
import '../models/work.dart';

class ApiClient {
  String baseUrl;
  ApiClient(this.baseUrl);

  Uri _u(String path) => Uri.parse('$baseUrl$path');

  Future<bool> ping() async {
    try {
      final r = await http
          .get(_u('/api/system/info'))
          .timeout(AppConfig.httpTimeout);
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>?> systemInfo() async {
    try {
      final r = await http
          .get(_u('/api/system/info'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        return jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (_) {}
    return null;
  }

  Future<List<String>> listPresets() async {
    try {
      final r = await http
          .get(_u('/api/presets'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        final data = jsonDecode(utf8.decode(r.bodyBytes));
        return (data['items'] as List).cast<String>();
      }
    } catch (_) {}
    return [];
  }

  Future<TaskItem?> createTask({
    required String type,
    required String prompt,
    Map<String, dynamic>? params,
  }) async {
    try {
      final r = await http
          .post(
            _u('/api/tasks'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'type': type,
              'prompt': prompt,
              'params': params ?? {},
            }),
          )
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200 || r.statusCode == 201) {
        return TaskItem.fromJson(
          jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>,
        );
      }
    } catch (_) {}
    return null;
  }

  Future<List<TaskItem>> listTasks({int limit = 50}) async {
    try {
      final r = await http
          .get(_u('/api/tasks?limit=$limit'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        final data = jsonDecode(utf8.decode(r.bodyBytes));
        return (data['items'] as List)
            .map((e) => TaskItem.fromJson(e as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return [];
  }

  Future<TaskItem?> getTask(String id) async {
    try {
      final r = await http
          .get(_u('/api/tasks/$id'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        return TaskItem.fromJson(
          jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>,
        );
      }
    } catch (_) {}
    return null;
  }

  Future<bool> cancelTask(String id) async {
    try {
      final r = await http
          .post(_u('/api/tasks/$id/cancel'))
          .timeout(AppConfig.httpTimeout);
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<List<WorkItem>> listWorks({int limit = 100}) async {
    try {
      final r = await http
          .get(_u('/api/works?limit=$limit'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        final data = jsonDecode(utf8.decode(r.bodyBytes));
        return (data['items'] as List)
            .map((e) => WorkItem.fromJson(e as Map<String, dynamic>))
            .toList();
      }
    } catch (_) {}
    return [];
  }

  /// 相对路径补成完整 URL，供 CachedNetworkImage 用
  String fileUrl(String path) {
    if (path.startsWith('http')) return path;
    return '$baseUrl$path';
  }
}