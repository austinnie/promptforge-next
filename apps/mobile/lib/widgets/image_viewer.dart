import 'dart:io';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// 全屏大图查看：支持双指缩放、拖动、下载/保存
class ImageViewerPage extends StatefulWidget {
  final String imageUrl;
  final String? heroTag;
  final String title;

  const ImageViewerPage({
    super.key,
    required this.imageUrl,
    this.heroTag,
    this.title = '预览',
  });

  @override
  State<ImageViewerPage> createState() => _ImageViewerPageState();
}

class _ImageViewerPageState extends State<ImageViewerPage> {
  bool _loading = true;

  @override
  Widget build(BuildContext context) {
    final image = Image.network(
      widget.imageUrl,
      fit: BoxFit.contain,
      loadingBuilder: (ctx, child, progress) {
        if (progress == null) {
          // 加载完成，去掉 loading
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted && _loading) setState(() => _loading = false);
          });
          return child;
        }
        return const Center(child: CircularProgressIndicator());
      },
      errorBuilder: (_, __, ___) => const Center(
        child: Icon(Icons.broken_image, size: 64, color: Colors.grey),
      ),
    );

    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black.withOpacity(0.7),
        foregroundColor: Colors.white,
        title: Text(
          widget.title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 14),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.copy),
            tooltip: '复制链接',
            onPressed: () {
              Clipboard.setData(ClipboardData(text: widget.imageUrl));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('已复制图片链接')),
              );
            },
          ),
        ],
      ),
      body: Center(
        child: InteractiveViewer(
          minScale: 0.8,
          maxScale: 5.0,
          child: widget.heroTag != null
              ? Hero(tag: widget.heroTag!, child: image)
              : image,
        ),
      ),
    );
  }
}

/// 说明：
///   - 移动端"保存图片"需要额外依赖 (如 image_gallery_saver / gal)
///   - Web 端浏览器内长按图片可直接另存为
///   - 需要保存到相册时，请自行集成 gal 或 image_gallery_saver