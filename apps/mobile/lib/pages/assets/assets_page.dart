import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../models/work.dart';
import '../../services/connection_manager.dart';

class AssetsPage extends StatefulWidget {
  const AssetsPage({super.key});
  @override
  State<AssetsPage> createState() => _AssetsPageState();
}

class _AssetsPageState extends State<AssetsPage> {
  List<WorkItem> _works = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _refresh());
  }

  Future<void> _refresh() async {
    setState(() => _loading = true);
    final cm = context.read<ConnectionManager>();
    final list = await cm.api.listWorks();
    if (!mounted) return;
    setState(() { _works = list; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    final cm = context.read<ConnectionManager>();

    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_works.isEmpty) {
      return RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(children: const [
          SizedBox(height: 200),
          Center(child: Text('暂无作品')),
        ]),
      );
    }
    return RefreshIndicator(
      onRefresh: _refresh,
      child: GridView.builder(
        padding: const EdgeInsets.all(8),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 8,
          mainAxisSpacing: 8,
        ),
        itemCount: _works.length,
        itemBuilder: (_, i) {
          final w = _works[i];
          return GestureDetector(
            onTap: () => _openBig(w),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: CachedNetworkImage(
                imageUrl: cm.api.fileUrl(w.url),
                fit: BoxFit.cover,
                placeholder: (_, __) =>
                    const Center(child: CircularProgressIndicator()),
                errorWidget: (_, __, ___) =>
                    const Icon(Icons.broken_image, size: 48),
              ),
            ),
          );
        },
      ),
    );
  }

  void _openBig(WorkItem w) {
    final cm = context.read<ConnectionManager>();
    showDialog(
      context: context,
      builder: (_) => Dialog(
        child: InteractiveViewer(
          child: CachedNetworkImage(imageUrl: cm.api.fileUrl(w.url)),
        ),
      ),
    );
  }
}