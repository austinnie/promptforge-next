import 'package:flutter/material.dart';

class PresetPicker extends StatelessWidget {
  final List<String> presets;
  final String? value;
  final ValueChanged<String?> onChanged;

  const PresetPicker({
    super.key,
    required this.presets,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
	return DropdownButtonFormField<String>(
	  initialValue: value,       // ← 改这里
	  decoration: const InputDecoration(
		labelText: '预设',
		border: OutlineInputBorder(),
	  ),
      items: presets
          .map((p) => DropdownMenuItem(value: p, child: Text(p)))
          .toList(),
      onChanged: onChanged,
    );
  }
}