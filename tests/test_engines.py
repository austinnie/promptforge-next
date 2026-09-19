#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P2 验收：engines 独立可跑。"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engines  # noqa: E402
from engines import dispatcher, factory, list_engines  # noqa: E402


async def main():
    print("=" * 60)
    print("  P2 验收 - engines")
    print("=" * 60)
    print()

    # 1. 注册表
    print("[1] 已注册引擎")
    all_engines = list_engines()
    for name, info in all_engines.items():
        configured = "✅" if factory.is_configured(name) else "⬜"
        caps = ", ".join(info["capabilities"])
        print(f"    {configured} {name:15} [{caps}]")
    print()

    # 2. 降级链
    print("[2] 各能力当前可用链")
    for cap, chain in dispatcher.describe_chain().items():
        print(f"    {cap:8} → {' → '.join(chain)}")
    print()

    # 3. mock 引擎出图
    print("[3] Mock 引擎出图")
    engine = factory.create("mock")
    img = await engine.generate_single("赛博朋克机甲少女", width=512, height=512)
    out = ROOT / "data" / "assets" / "test_mock.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"    ✅ 尺寸: {img.size}, 保存: {out.relative_to(ROOT)}")
    print()

    # 4. dispatcher 走一遍（会先试 agnes，没 key 会跳过，最终到 mock）
    print("[4] Dispatcher 降级验证（prompt → prefer=mock）")
    img2, used = await dispatcher.generate_image(
        "月光下的森林，机甲少女背影",
        width=512, height=512,
        prefer="mock",
    )
    out2 = ROOT / "data" / "assets" / "test_dispatcher.png"
    img2.save(out2)
    print(f"    ✅ 使用引擎: {used}, 尺寸: {img2.size}")
    print()

    # 5. 可选：pollinations 真实出图
    if factory.is_configured("pollinations"):
        print("[5] Pollinations 真实出图（可能耗时 10-30 秒）")
        try:
            img3, used3 = await dispatcher.generate_image(
                "a beautiful sunset over the ocean",
                width=768, height=768,
                prefer="pollinations",
            )
            out3 = ROOT / "data" / "assets" / "test_pollinations.png"
            img3.save(out3)
            print(f"    ✅ 使用引擎: {used3}, 尺寸: {img3.size}")
        except Exception as e:
            print(f"    ⚠️ 失败（不影响 P2 验收）: {e}")
    else:
        print("[5] Pollinations 未配置（跳过真实出图）")
        print("    想测真实出图：在 .env 里填 POLLINATIONS_API_KEY")
    print()

    print("=" * 60)
    print("  🎉 P2 验收通过")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())