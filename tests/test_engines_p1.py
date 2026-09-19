#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""engines 第一批移植验收：agnes / pollinations / freeapi。

用法：
    python tests/test_engines_p1.py

行为：
    - 只对"已配置"的引擎做真实调用（无 key 时自动跳过）
    - freeapi 无需 key，会真的尝试出图（但会因代理不稳定而失败，不影响）
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engines  # noqa: E402
from engines import dispatcher, factory, list_engines  # noqa: E402

OUT_DIR = ROOT / "data" / "assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    print("=" * 60)
    print("  engines 第一批（agnes / pollinations / freeapi）")
    print("=" * 60)

    print("\n[1] 引擎注册表")
    all_engines = list_engines()
    for name, info in all_engines.items():
        configured = "✅" if factory.is_configured(name) else "⬜"
        caps = ", ".join(info["capabilities"])
        print(f"    {configured} {name:15} [{caps}]")

    print("\n[2] 降级链")
    for cap, chain in dispatcher.describe_chain().items():
        print(f"    {cap:8} → {' → '.join(chain)}")

    print("\n[3] Agnes t2i")
    if factory.is_configured("agnes"):
        try:
            engine = factory.create("agnes")
            img = await engine.generate_single(
                "a serene mountain lake at dawn, soft mist",
                width=1024, height=1024, seed=42,
            )
            out = OUT_DIR / "test_agnes.png"
            img.save(out)
            print(f"    ✅ 尺寸: {img.size}, 保存: {out.relative_to(ROOT)}")
        except Exception as e:
            print(f"    ⚠️ 失败: {e}")
    else:
        print("    ⬜ 未配置（设置 .env 里的 AGNES_API_KEY）")

    print("\n[4] Pollinations t2i（含中文翻译）")
    if factory.is_configured("pollinations"):
        try:
            engine = factory.create("pollinations")
            img = await engine.generate_single(
                "月光下的森林，一只白鹿站在溪边",
                width=768, height=768,
            )
            out = OUT_DIR / "test_pollinations.png"
            img.save(out)
            print(f"    ✅ 尺寸: {img.size}, 保存: {out.relative_to(ROOT)}")
        except Exception as e:
            print(f"    ⚠️ 失败: {e}")
    else:
        print("    ⬜ 未配置（设置 .env 里的 POLLINATIONS_API_KEY）")

    print("\n[5] FreeAPI t2i")
    if factory.is_configured("freeapi"):
        try:
            engine = factory.create("freeapi")
            img = await engine.generate_single(
                "a cat sitting on a windowsill, morning light",
                width=1024, height=1024,
            )
            out = OUT_DIR / "test_freeapi.png"
            img.save(out)
            print(f"    ✅ 尺寸: {img.size}, 保存: {out.relative_to(ROOT)}")
        except Exception as e:
            print(f"    ⚠️ 失败（FreeAPI 代理不稳定，正常）: {str(e)[:120]}")
    else:
        print("    ⬜ 未配置")

    print("\n[6] Dispatcher 降级验证")
    img, used = await dispatcher.generate_image(
        "a cozy wooden cabin in the snow, warm light from windows",
        width=768, height=768,
    )
    out = OUT_DIR / "test_dispatcher_p1.png"
    img.save(out)
    print(f"    ✅ 使用引擎: {used}")
    print(f"      保存: {out.relative_to(ROOT)}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())