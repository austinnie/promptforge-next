// lib/services/agnes_config.dart
import 'package:shared_preferences/shared_preferences.dart';

/// Agnes 配置（从手机本地读写）。
class AgnesConfig {
  static const _kApiKey = 'agnes_api_key';
  static const _kBaseUrl = 'agnes_base_url';
  static const _kImageModel = 'agnes_image_model';

  static const defaultBaseUrl = 'https://apihub.agnes-ai.com/v1';
  static const defaultImageModel = 'agnes-image-2.1-flash';

  /// 可选路由：主路由失败时依次尝试
  static const fallbackRoutes = [
    'https://apihub.agnes-ai.com/v1',
    'https://apihub.agnes-ai.cn/v1',
  ];

  String apiKey;
  String baseUrl;
  String imageModel;

  AgnesConfig({
    this.apiKey = '',
    this.baseUrl = defaultBaseUrl,
    this.imageModel = defaultImageModel,
  });

  bool get isReady => apiKey.isNotEmpty;

  /// 从本地读
  static Future<AgnesConfig> load() async {
    final sp = await SharedPreferences.getInstance();
    return AgnesConfig(
      apiKey: sp.getString(_kApiKey) ?? '',
      baseUrl: sp.getString(_kBaseUrl) ?? defaultBaseUrl,
      imageModel: sp.getString(_kImageModel) ?? defaultImageModel,
    );
  }

  /// 保存到本地
  Future<void> save() async {
    final sp = await SharedPreferences.getInstance();
    await sp.setString(_kApiKey, apiKey);
    await sp.setString(_kBaseUrl, baseUrl);
    await sp.setString(_kImageModel, imageModel);
  }

  /// 清空
  Future<void> clear() async {
    final sp = await SharedPreferences.getInstance();
    await sp.remove(_kApiKey);
    await sp.remove(_kBaseUrl);
    await sp.remove(_kImageModel);
  }
}