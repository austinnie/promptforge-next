// lib/services/agnes_direct.dart
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'agnes_config.dart';

/// 直连 Agnes 图像 API 的客户端。
///
/// 生图逻辑参考 PromptForge-Next 的 engines/agnes.py：
///   POST {base_url}/images/generations
///   body: { model, prompt, n, size: "1K"/"2K"..., response_format: "url", seed }
/// 返回可能是 { data: [{ url }] } 或 { output: { results: [{url}] } }
class AgnesDirect {
  final AgnesConfig config;

  AgnesDirect(this.config);

  /// 文生图，返回图片字节。
  Future<Uint8List> generateImage({
    required String prompt,
    String negative = '',
    int width = 1024,
    int height = 1024,
    int? seed,
  }) async {
    if (!config.isReady) {
      throw Exception('未配置 Agnes API Key，请到「设置」里填写');
    }
    if (prompt.trim().isEmpty) {
      throw Exception('prompt 不能为空');
    }

    final body = <String, dynamic>{
      'model': config.imageModel,
      'prompt': prompt,
      'n': 1,
      'size': _toSizeTier(width, height),
      'response_format': 'url',
      'seed': _clampSeed(seed),
    };

    final result = await _postWithFallback('/images/generations', body);
    final imageUrl = _extractImageUrl(result);
    if (imageUrl == null) {
      throw Exception('Agnes 未返回图片: ${jsonEncode(result).substring(0, 200)}');
    }
    return _downloadImage(imageUrl);
  }

  /// 图生图：给一张参考图 + 提示词。
  Future<Uint8List> imageToImage({
    required String prompt,
    required Uint8List imageBytes,
    double strength = 0.7,
    int width = 1024,
    int height = 1024,
    int? seed,
  }) async {
    if (!config.isReady) {
      throw Exception('未配置 Agnes API Key，请到「设置」里填写');
    }
    if (prompt.trim().isEmpty) {
      throw Exception('prompt 不能为空');
    }

    final b64 = base64Encode(imageBytes);
    final body = <String, dynamic>{
      'model': config.imageModel,
      'prompt': prompt,
      'n': 1,
      'size': _toSizeTier(width, height),
      'seed': _clampSeed(seed),
      'extra_body': {
        'image': ['data:image/png;base64,$b64'],
        'response_format': 'url',
      },
      if (strength > 0 && strength < 1) 'strength': strength,
    };

    final result = await _postWithFallback('/images/generations', body);
    final imageUrl = _extractImageUrl(result);
    if (imageUrl == null) {
      throw Exception('Agnes i2i 未返回图片: ${jsonEncode(result).substring(0, 200)}');
    }
    return _downloadImage(imageUrl);
  }

  /// 简单的 ping：调 /chat/completions 验证 key 是否有效。
  Future<bool> ping() async {
    if (!config.isReady) return false;
    try {
      final url = Uri.parse('${config.baseUrl}/chat/completions');
      final resp = await http
          .post(
            url,
            headers: _headers(),
            body: jsonEncode({
              'model': 'agnes-2.5-flash',
              'messages': [
                {'role': 'user', 'content': 'hi'},
              ],
              'max_tokens': 5,
            }),
          )
          .timeout(const Duration(seconds: 30));
      return resp.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ==================== 内部 ====================

  Map<String, String> _headers() => {
        'Authorization': 'Bearer ${config.apiKey}',
        'Content-Type': 'application/json',
      };

  /// POST 请求，多路由 fallback。
  Future<Map<String, dynamic>> _postWithFallback(
    String path,
    Map<String, dynamic> body,
  ) async {
    // 路由顺序：配置的 baseUrl 优先，然后其他备用
    final routes = <String>[config.baseUrl];
    for (final r in AgnesConfig.fallbackRoutes) {
      if (r != config.baseUrl) routes.add(r);
    }

    Exception? lastErr;
    for (final route in routes) {
      try {
        final url = Uri.parse('$route$path');
        debugPrint('[agnes] POST $url');

        final resp = await http
            .post(url, headers: _headers(), body: jsonEncode(body))
            .timeout(const Duration(seconds: 180));

        if (resp.statusCode == 200) {
          return jsonDecode(utf8.decode(resp.bodyBytes)) as Map<String, dynamic>;
        }

        // 401/403 = key 或权限问题，换路由也没用，直接抛
        if (resp.statusCode == 401 || resp.statusCode == 403) {
          throw Exception('Agnes HTTP ${resp.statusCode}: ${_short(resp.body)}');
        }

        // 503 = 服务繁忙，试试下一个路由
        if (resp.statusCode == 503) {
          lastErr = Exception('Agnes 服务繁忙 (503): ${_short(resp.body)}');
          continue;
        }

        // 其他错误直接抛
        throw Exception('Agnes HTTP ${resp.statusCode}: ${_short(resp.body)}');
      } catch (e) {
        lastErr = e is Exception ? e : Exception(e.toString());
        continue;
      }
    }

    throw lastErr ?? Exception('Agnes 所有路由均失败');
  }

  String _short(String s) => s.length > 200 ? s.substring(0, 200) : s;

  int _clampSeed(int? seed) {
    if (seed == null) return DateTime.now().millisecondsSinceEpoch % 1000;
    return seed.clamp(-1, 999);
  }

  String _toSizeTier(int w, int h) {
    final m = w > h ? w : h;
    if (m <= 1024) return '1K';
    if (m <= 2048) return '2K';
    if (m <= 3072) return '3K';
    return '4K';
  }

  String? _extractImageUrl(Map<String, dynamic> data) {
    // 情况 1: { data: [{ url }] }
    final list = data['data'];
    if (list is List && list.isNotEmpty) {
      final u = list[0]['url'];
      if (u != null) return u.toString();
    }
    // 情况 2: { output: { results: [{url}] } }
    final out = data['output'];
    if (out is Map) {
      final results = out['results'];
      if (results is List && results.isNotEmpty) {
        final u = results[0]['url'];
        if (u != null) return u.toString();
      }
      final u = out['image_url'];
      if (u != null) return u.toString();
    }
    return null;
  }

  /// 从 URL 下载图片；支持 data:image base64。
  Future<Uint8List> _downloadImage(String url) async {
    if (url.startsWith('data:image')) {
      final b64 = url.split(',').last;
      return base64Decode(b64);
    }
    final resp = await http
        .get(Uri.parse(url))
        .timeout(const Duration(seconds: 60));
    if (resp.statusCode != 200) {
      throw Exception('下载图片失败: ${resp.statusCode}');
    }
    return resp.bodyBytes;
  }
}