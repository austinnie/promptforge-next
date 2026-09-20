#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""image_curator 验收。

用法：
    python tests/test_image_curator.py

依赖：
    - 有 agnes key
    - 有 python-docx
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.image_curator import ImageCurator  # noqa: E402


async def main():
    print("=" * 60)
    print("  image_curator 验收")
    print("=" * 60)

    ic = ImageCurator()

    # 用之前生成的测试图片
    test_dir = ROOT / "data" / "assets"
    images = list(test_dir.glob("*.png"))[:3]

    if not images:
        print("\n❌ data/assets 里没有 png 图片，先跑 test_i2i.py 生成底图")
        return

    print(f"\n[1] 用 directory 模式处理 {len(images)} 张图")
    r = await ic.execute(
        action="curate",
        directory=str(test_dir),
        title="测试作品集",
        max_images=3,
        with_intro=True,
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    标题: {res['title']}")
        print(f"    图片数: {res['image_count']}")
        print(f"    耗时: {res['elapsed']}")
        print(f"    Markdown: {res['article_path']}")
        print(f"    HTML:     {res['html_path']}")
        print(f"    Word:     {res['docx_path']}")
        print(f"    富文本:   {res['clipboard_path']}")
    else:
        print(f"    错误: {r['error']}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())