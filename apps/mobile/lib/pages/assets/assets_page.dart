import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/work.dart';
import '../../services/connection_manager.dart';
import '../../widgets/image_viewer.dart';

class AssetsPage extends StatefulWidget {
  const AssetsPage({super.key});
  @override
  State<AssetsPage> createState() => _AssetsPageState();
}

class _AssetsPageState extends State<AssetsPage> {
  List<WorkItem> _works = [];
  bool _firstLoading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _refresh());
  }

  Future<void> _refresh() async {
    final cm = context.read<ConnectionManager>();
    final list = await cm.api.listWorks(limit: 100);
    if (!mounted) return;
    setState(() {
      _works = list;
      _firstLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final fileUrl = context.read<ConnectionManager>().api.fileUrl;

    return RefreshIndicator(
      onRefresh: _refresh,
      child: _firstLoading
          ? const Center(child: CircularProgressIndicator())
          : _works.isEmpty
              ? _buildEmpty()
              : GridView.builder(
                  padding: const EdgeInsets.all(8),
                  physics: const AlwaysScrollableScrollPhysics(),
                  gridDelegate:
                      const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    crossAxisSpacing: 8,
                    mainAxisSpacing: 8,
                    childAspectRatio: 1.0,
                  ),
                  itemCount: _works.length,
                  itemBuilder: (ctx, i) {
                    final w = _works[i];
                    final url = fileUrl(w.url);
                    return GestureDetector(
                      onTap: () => _openViewer(w, url),
                      child: Hero(
                        tag: 'work-${w.id}',
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Stack(
                            fit: StackFit.expand,
                            children: [
                              Image.network(
                                url,
                                fit: BoxFit.cover,
                                loadingBuilder: (ctx, child, progress) {
                                  if (progress == null) return child;
                                  return Container(
                                    color: Colors.grey.shade100,
                                    child: const Center(
                                      child: SizedBox(
                                        width: 24,
                                        height: 24,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2),
                                      ),
                                    ),
                                  );
                                },
                                errorBuilder: (_, __, ___) => Container(
                                  color: Colors.grey.shade200,
                                  child: const Icon(Icons.broken_image,
                                      color: Colors.grey),
                                ),
                              ),
                              // 底部渐变 + prompt 文字
                              if (w.prompt != null && w.prompt!.isNotEmpty)
                                Positioned(
                                  left: 0,
                                  right: 0,
                                  bottom: 0,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 8, vertical: 6),
                                    decoration: BoxDecoration(
                                      gradient: LinearGradient(
                                        begin: Alignment.topCenter,
                                        end: Alignment.bottomCenter,
                                        colors: [
                                          Colors.transparent,
                                          Colors.black.withOpacity(0.6),
                                        ],
                                      ),
                                    ),
                                    child: Text(
                                      w.prompt!,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    );
                  },
                ),
    );
  }

  Widget _buildEmpty() {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 200),
        Icon(Icons.photo_library_outlined,
            size: 64, color: Colors.grey.shade400),
        const SizedBox(height: 16),
        const Center(
          child: Text(
            '还没有作品\n生成完成的图片会出现在这里',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.grey),
          ),
        ),
      ],
    );
  }

  void _openViewer(WorkItem work, String imageUrl) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ImageViewerPage(
          imageUrl: imageUrl,
          heroTag: 'work-${work.id}',
          title: work.prompt ?? work.id,
        ),
      ),
    );
  }
}