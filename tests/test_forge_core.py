#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P1 验收：forge_core 独立可跑，不依赖 GUI / settings / 本地模型。"""

import sys
from pathlib import Path

# 把 packages 加进 sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from forge_core import (  # noqa: E402
    IntentAnalyzer,
    PresetBridge,
    PromptComposer,
    SafetyChecker,
    get_default_bridge,
)


def main():
    print("=" * 60)
    print("  P1 验收 - forge_core")
    print("=" * 60)
    print()

    # 1. Bridge 初始化
    print("[1] 初始化 PresetBridge")
    bridge = PresetBridge()
    assert bridge.is_ready(), "❌ PresetBridge 未就绪"

    layer_info = bridge.get_layer_info()
    print(f"    层选项数: {layer_info}")
    assert len(layer_info) == 6, f"❌ 期望 6 层，实际 {len(layer_info)}"
    print()

    # 2. 预设列表
    print("[2] 加载预设列表")
    presets = bridge.list_presets()
    print(f"    共 {len(presets)} 个预设")
    assert len(presets) > 50, f"❌ 预设太少: {len(presets)}"
    print(f"    样例: {presets[:5]}")
    print()

    # 3. 按关键词查找预设
    print("[3] 关键词查找预设")
    for kw in ["机甲", "水墨", "龙", "风景"]:
        found = bridge.find_preset_by_keyword(f"给我来个{kw}风格")
        print(f"    {kw} → {found}")
    print()

    # 4. 构建 prompt
    print("[4] 构建 prompt")
    prompt, detail = bridge.build_prompt(
        preset="mecha_glow",
        mode="random",
        subject_override="赛博朋克机甲少女",
        seed=42,
        return_detail=True,
    )
    print(f"    Prompt: {prompt[:120]}...")
    print(f"    层详情 keys: {list(detail.keys())}")
    assert "subject" in detail
    assert "赛博朋克机甲少女" in detail["subject"]
    print()

    # 5. 意图分析
    print("[5] 意图分析")
    analyzer = IntentAnalyzer(enable_safety_check=True, preset_bridge=bridge)
    cases = [
        ("生成一张美丽的日落风景", False),
        ("用机甲风格画一个少女", False),
        ("把这张图改成油画风格", True),
        ("你好啊", False),
    ]
    for text, has_img in cases:
        r = analyzer.analyze(text, has_image=has_img)
        print(f"    {text!r:30} → {r.type}")
    print()

    # 6. 安全检查
    print("[6] 安全检查")
    safe_text = "美丽的日落风景"
    unsafe_text = "全裸写真"
    print(f"    {safe_text!r} → safe={SafetyChecker.check(safe_text)[0]}")
    print(f"    {unsafe_text!r} → safe={SafetyChecker.check(unsafe_text)[0]}")
    assert SafetyChecker.check(safe_text)[0] is False
    assert SafetyChecker.check(unsafe_text)[0] is True
    sanitized = SafetyChecker.sanitize(unsafe_text)
    print(f"    sanitize({unsafe_text!r}) → {sanitized!r}")
    print()

    # 7. 组合器直接使用
    print("[7] PromptComposer 直接使用")
    from forge_core.loader import load_all_layers
    layers = load_all_layers(ROOT / "packages" / "forge_core" / "layers")
    composer = PromptComposer(layers)
    print(f"    总组合数: {composer.get_total_combinations():,}")
    print()

    print("=" * 60)
    print("  🎉 P1 验收通过")
    print("=" * 60)


if __name__ == "__main__":
    main()