import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../core/app_config.dart';
import '../models/task.dart';
import '../models/work.dart';

class ApiClient {
  String baseUrl;
  ApiClient(this.baseUrl);

  // ===========================================================================
  // 后端真实路由（与 server/api/v1/*.py 对齐）：
  //   GET  /api/v1/system/info
  //   GET  /api/v1/engines
  //   GET  /api/v1/presets
  //   GET  /api/v1/presets/{name}
  //   GET  /api/v1/jobs
  //   POST /api/v1/jobs/image             ← 文生图
  //   POST /api/v1/jobs/image-to-image    ← 图生图
  //   GET  /api/v1/jobs/{job_id}
  //   GET  /files/{key}                   ← 不带 /api/v1 前缀
  // ===========================================================================

  String get _apiBase {
    final b = baseUrl;
    if (b.endsWith('/api/v1')) return b;
    if (b.endsWith('/api')) return '${b.substring(0, b.length - 4)}/api/v1';
    if (b.endsWith('/')) return '${b}api/v1';
    return '$b/api/v1';
  }

  String get _hostBase {
    final b = baseUrl;
    if (b.endsWith('/api/v1')) return b.substring(0, b.length - 7);
    if (b.endsWith('/api')) return b.substring(0, b.length - 4);
    if (b.endsWith('/')) return b.substring(0, b.length - 1);
    return b;
  }

  Uri _u(String path) {
    if (path.startsWith('/files/') || path == '/files') {
      return Uri.parse('$_hostBase$path');
    }
    return Uri.parse('$_apiBase$path');
  }

  // ===========================================================================
  // System
  // ===========================================================================

  Future<bool> ping() async {
    try {
      final r = await http
          .get(_u('/system/info'))
          .timeout(AppConfig.httpTimeout);
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>?> systemInfo() async {
    try {
      final r = await http
          .get(_u('/system/info'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        return jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;
      }
    } catch (e) {
      debugPrint('[api_client] $e');
    }
    return null;
  }

  // ===========================================================================
  // Presets
  // ===========================================================================

  Future<List<String>> listPresets() async {
    try {
      final r = await http
          .get(_u('/presets'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        final data = jsonDecode(utf8.decode(r.bodyBytes));
        final result = <String>[];

        if (data is Map) {
          for (final entry in data.entries) {
            final cat = entry.key.toString();
            final v = entry.value;
            if (v is List) {
              for (final item in v) {
                if (item is Map) {
                  final display = item['display']?.toString();
                  final name = item['name']?.toString();
                  final label = (display != null && display.isNotEmpty)
                      ? display
                      : name;
                  if (label != null && label.isNotEmpty) {
                    result.add('[$cat] $label');
                  }
                } else if (item is String) {
                  result.add('[$cat] $item');
                }
              }
            }
          }
        } else if (data is List) {
          for (final item in data) {
            if (item is String) {
              result.add(item);
            } else if (item is Map) {
              final d = item['display'] ?? item['name'];
              if (d != null) result.add(d.toString());
            }
          }
        }
        return result;
      }
    } catch (e) {
      debugPrint('[listPresets] $e');
    }
    return [];
  }

  // ===========================================================================
  // Jobs
  // ===========================================================================

  /// 文生图：POST /api/v1/jobs/image
  Future<TaskItem?> createTask({
    required String type,
    required String prompt,
    Map<String, dynamic>? params,
  }) async {
    try {
      final p = params ?? <String, dynamic>{};

      final body = <String, dynamic>{
        'prompt': prompt,
        'width': (p['width'] as num?)?.toInt() ?? 1024,
        'height': (p['height'] as num?)?.toInt() ?? 1024,
        if (p['preset'] != null) 'preset': p['preset'],
        if (p['engine'] != null) 'engine': p['engine'],
      };

      final r = await http
          .post(
            _u('/jobs/image'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(AppConfig.httpTimeout);

      if (r.statusCode != 200 && r.statusCode != 201 && r.statusCode != 202) {
        debugPrint('[createTask] HTTP ${r.statusCode}: ${r.body}');
        return null;
      }

      final created =
          jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;

      if (created['created_at'] != null) {
        return TaskItem.fromJson(created);
      }

      final jobId = (created['id'] ?? created['job_id']) as String?;
      if (jobId == null) return null;
      return await getTask(jobId);
    } catch (e, st) {
      debugPrint('[createTask] error: $e\n$st');
      return null;
    }
  }

  /// 图生图：POST /api/v1/jobs/image-to-image
  ///
  /// 请求体：
  ///   { prompt, image_base64, strength, width, height, engine? }
  Future<TaskItem?> createImageToImageTask({
    required String prompt,
    required Uint8List imageBytes,
    double strength = 0.7,
    int width = 1024,
    int height = 1024,
    String? engine,
  }) async {
    try {
      final b64 = base64Encode(imageBytes);

      final body = <String, dynamic>{
        'prompt': prompt,
        'image_base64': b64,
        'strength': strength,
        'width': width,
        'height': height,
        if (engine != null && engine.isNotEmpty) 'engine': engine,
      };

      final r = await http
          .post(
            _u('/jobs/image-to-image'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(AppConfig.httpTimeout);

      if (r.statusCode != 200 && r.statusCode != 201 && r.statusCode != 202) {
        debugPrint('[createI2I] HTTP ${r.statusCode}: ${r.body}');
        return null;
      }

      final created =
          jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;

      if (created['created_at'] != null) {
        return TaskItem.fromJson(created);
      }

      final jobId = (created['id'] ?? created['job_id']) as String?;
      if (jobId == null) return null;
      return await getTask(jobId);
    } catch (e, st) {
      debugPrint('[createI2I] error: $e\n$st');
      return null;
    }
  }

  Future<List<TaskItem>> listTasks({int limit = 50}) async {
    try {
      final r = await http
          .get(_u('/jobs?limit=$limit'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        final data = jsonDecode(utf8.decode(r.bodyBytes));
        final list = (data is Map && data['items'] is List)
            ? data['items'] as List
            : (data as List);
        return list
            .map((e) => TaskItem.fromJson(e as Map<String, dynamic>))
            .toList();
      }
    } catch (e) {
      debugPrint('[listTasks] $e');
    }
    return [];
  }

  Future<TaskItem?> getTask(String id) async {
    try {
      final r = await http
          .get(_u('/jobs/$id'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        return TaskItem.fromJson(
          jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>,
        );
      }
    } catch (e) {
      debugPrint('[getTask] $e');
    }
    return null;
  }

  Future<bool> cancelTask(String id) async {
    return false;
  }

  // ===========================================================================
  // Works（后端暂无 /works 接口，临时映射到 /jobs）
  // ===========================================================================

  Future<List<WorkItem>> listWorks({int limit = 100}) async {
    try {
      final r = await http
          .get(_u('/jobs?limit=$limit'))
          .timeout(AppConfig.httpTimeout);
      if (r.statusCode == 200) {
        final data = jsonDecode(utf8.decode(r.bodyBytes));
        final list = (data is Map && data['items'] is List)
            ? data['items'] as List
            : (data as List);
        return list
            .map((e) => WorkItem.fromJson(e as Map<String, dynamic>))
            .where((w) => w.url.isNotEmpty)
            .toList();
      }
      debugPrint('[listWorks] HTTP ${r.statusCode}: ${r.body}');
    } catch (e) {
      debugPrint('[listWorks] error: $e');
    }
    return [];
  }

  // ===========================================================================
  // File URL
  // ===========================================================================

  String fileUrl(String path) {
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return path;
    }
    if (path.startsWith('/files/')) {
      return '$_hostBase$path';
    }
    if (path.startsWith('/')) {
      return '$_hostBase/files$path';
    }
    return '$_hostBase/files/$path';
  }
}