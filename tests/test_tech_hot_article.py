#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""tech_hot_article 验收。

用法：
    python tests/test_tech_hot_article.py

注意：
    - 会联网抓 RSS
    - 会消耗 agnes 额度（1 篇文章 + 1-3 张配图）
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.tech_hot_article import TechHotArticle  # noqa: E402


async def main():
    print("=" * 60)
    print("  tech_hot_article 验收")
    print("=" * 60)

    ta = TechHotArticle()

    # 1. 列热点
    print("\n[1] list_hot")
    r = await ta.execute(action="list_hot")
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        items = r["result"]["hot_items"]
        print(f"    热点数: {len(items)}")
        for i, it in enumerate(items[:3]):
            print(f"      {i}. [{it['source']}] {it['title'][:60]}")
    else:
        print(f"    错误: {r['error']}")

    # 2. 生成文章
    print("\n[2] generate（1 篇）")
    r = await ta.execute(
        action="generate",
        style="通俗科普型",
        article_words=800,
        with_images=True,
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    标题: {res['title']}")
        print(f"    热点: {res['hot_topic'][:60]}")
        print(f"    风格: {res['style']}")
        print(f"    字数: {res['word_count']}")
        print(f"    配图数: {res['image_count']}")
        print(f"    Word: {res['word_file']}")
        print(f"    耗时: {res['elapsed']}")
    else:
        print(f"    错误: {r['error']}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())