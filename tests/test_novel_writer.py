#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""novel_writer 验收。

用法：
    python tests/test_novel_writer.py

注意：会消耗 agnes 额度（3 章约 5000 tokens）。
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.novel_writer import NovelWriter  # noqa: E402


async def main():
    print("=" * 60)
    print("  novel_writer 验收")
    print("=" * 60)

    nw = NovelWriter()

    # 1. 列出语言
    print("\n[1] list_languages")
    r = await nw.execute(action="list_languages")
    print(f"    语言数: {len(r['result']['languages'])}")

    # 2. 生成短小说（1 章）
    print("\n[2] generate（1 章，中文）")
    r = await nw.execute(
        action="generate",
        title="星际旅客",
        genre="科幻",
        outline="一名宇航员在遥远的星系中醒来，发现自己失去了记忆。",
        characters="艾琳：女主角，冷静理性的宇航员。AI-07：飞船的人工智能。",
        chapter_count=1,
        words_per_chapter=300,
        language="zh",
        style="冷峻而富有诗意",
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    标题: {res['title']}")
        print(f"    章节: {res['chapter_count']} 章")
        print(f"    字数: {res['total_words']}")
        print(f"    文件: {res['saved_to']}")
        print(f"    URL: {res['file_url']}")
        print(f"    耗时: {res['generation_time']}")
        print(f"\n    简介: {res['summary'][:100]}...")
        if res["chapters"]:
            print(f"\n    第 1 章标题: {res['chapters'][0]['title']}")
            print(f"    第 1 章内容前 200 字:\n{res['chapters'][0]['content'][:200]}...")
    else:
        print(f"    错误: {r['error']}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())