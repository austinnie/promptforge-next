# packages/forge_core/loader.py
"""动态加载 6 层素材。"""

import importlib.util
import sys
from pathlib import Path


def load_all_layers(layers_dir: str | Path) -> dict:
    """加载 layers_dir 下所有 layer_*.py，返回 {layer_name: [选项...]}。

    文件名约定：layer_01_subject.py → 层名 subject
    """
    layers_dir = Path(layers_dir)
    layers: dict[str, list] = {}

    if not layers_dir.exists():
        return layers

    for filename in sorted(p for p in layers_dir.iterdir() if p.is_file()):
        name = filename.name
        if not name.startswith("layer_") or not name.endswith(".py"):
            continue

        # layer_01_subject.py → subject
        layer_name = name[len("layer_"):-len(".py")]
        # 去掉前导的 01_ 02_ 前缀
        if "_" in layer_name:
            layer_name = layer_name.split("_", 1)[1]

        spec = importlib.util.spec_from_file_location(layer_name, str(filename))
        if spec is None or spec.loader is None:
            print(f"   ⚠️ 跳过 {name}: 无法加载")
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules[layer_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"   ⚠️ 跳过 {name}: {e}")
            continue

        if hasattr(module, "LAYER") and isinstance(module.LAYER, list):
            layers[layer_name] = module.LAYER
            print(f"   ✅ 加载层: {layer_name} ({len(module.LAYER)} 个选项)")
        else:
            print(f"   ⚠️ 跳过 {name}: 未找到 LAYER 列表")

    return layers