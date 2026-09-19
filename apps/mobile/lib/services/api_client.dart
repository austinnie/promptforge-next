import 'dart:convert';
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
  //   POST /api/v1/jobs/image       ← 创建图片任务的唯一接口
  //   GET  /api/v1/jobs/{job_id}
  //   GET  /files/{key}             ← 注意：这个不带 /api/v1 前缀
  // ===========================================================================

  /// 业务 API 基址，自动补 /api/v1
  String get _apiBase {
    final b = baseUrl;
    if (b.endsWith('/api/v1')) return b;
    if (b.endsWith('/api')) return '${b.substring(0, b.length - 4)}/api/v1';
    if (b.endsWith('/')) return '${b}api/v1';
    return '$b/api/v1';
  }

  /// 主机基址（用于 /files 这种不带 /api/v1 的静态资源）
  String get _hostBase {
    final b = baseUrl;
    if (b.endsWith('/api/v1')) return b.substring(0, b.length - 7);
    if (b.endsWith('/api')) return b.substring(0, b.length - 4);
    if (b.endsWith('/')) return b.substring(0, b.length - 1);
    return b;
  }

  /// 拼接完整 URL
  /// - /files/xxx 走 host（不带 /api/v1）
  /// - 其他都走 /api/v1
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
    } catch (e) { print('[api_client] $e'); }
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

        // 后端返回：{"机甲": [{name, display}, ...], "国风": [...], ...}
        if (data is Map) {
          for (final entry in data.entries) {
            final v = entry.value;
            if (v is List) {
              for (final item in v) {
                if (item is Map) {
                  final display = item['display']?.toString();
                  final name = item['name']?.toString();
                  if (display != null && display.isNotEmpty) {
                    result.add(display);
                  } else if (name != null && name.isNotEmpty) {
                    result.add(name);
                  }
                } else if (item is String) {
                  result.add(item);
                }
              }
            }
          }
        } else if (data is List) {
          // 兼容扁平列表
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
      // ignore: avoid_print
      print('[listPresets] $e');
    }
    return [];
  }

  // ===========================================================================
  // Jobs（旧名 tasks）
  // ===========================================================================

  /// 创建图片任务
  /// 后端接口：POST /api/v1/jobs/image
  /// 请求体：{prompt, width, height, engine?, preset?}
  /// ⚠️ 若后端 ImageJobRequest 字段不同，请按 jobs.py 调整 body。
  /// 创建图片任务
  /// 后端：POST /api/v1/jobs/image  →  返回完整 Job.to_dict()
  Future<TaskItem?> createTask({
    required String type,
    required String prompt,
    Map<String, dynamic>? params,
  }) async {
    try {
      final p = params ?? <String, dynamic>{};

      // 后端 ImageJobRequest 只认这 4 个字段
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

      // 后端返回 202 Accepted
      if (r.statusCode != 200 && r.statusCode != 201 && r.statusCode != 202) {
        // 临时打印，方便你在 Flutter 控制台看到真实错误
        // ignore: avoid_print
        print('[createTask] HTTP ${r.statusCode}: ${r.body}');
        return null;
      }

      final created =
          jsonDecode(utf8.decode(r.bodyBytes)) as Map<String, dynamic>;

      // 如果返回的是完整 job dict（有 created_at），直接解析
      if (created['created_at'] != null) {
        return TaskItem.fromJson(created);
      }

      // 兼容旧版：只返回 {job_id, status}，再 GET 一次拿完整信息
      final jobId = (created['id'] ?? created['job_id']) as String?;
      if (jobId == null) return null;
      return await getTask(jobId);
    } catch (e, st) {
      // 临时打印，定位完可以删掉
      // ignore: avoid_print
      print('[createTask] error: $e\n$st');
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
    } catch (e) { print('[api_client] $e'); }
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
    } catch (e) { print('[api_client] $e'); }
    return null;
  }

  /// ⚠️ 后端目前没有取消任务的接口，先保留占位返回 false
  Future<bool> cancelTask(String id) async {
    return false;
  }

  // ===========================================================================
  // Works（后端暂无 /works 接口，临时映射到 /jobs）
  // ===========================================================================

  /// ⚠️ 后端暂时没有 /works 接口，这里暂时读 /jobs。
  /// 待后端补充 GET /api/v1/works 后，把下面路径改回 '/works?limit=$limit' 即可。
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
            .where((w) => w.url.isNotEmpty)      // 过滤掉还没生成成功的
            .toList();
      }
    } catch (_) {}
    return [];
  }

  // ===========================================================================
  // File URL（静态资源，不带 /api/v1）
  // ===========================================================================

  /// 把后端返回的 file key 拼成完整 URL，供 CachedNetworkImage 用
  /// 例：key='abc.png' -> 'http://localhost:8000/files/abc.png'
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