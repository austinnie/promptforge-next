#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""daily_pipeline 验收。

默认只跑「3 张图 + 鉴赏 + 排版，不推送」的最小流程。
全流程会消耗大量 agnes 额度（6 图 + vision + 排版），谨慎运行。

用法：
    python tests/test_daily_pipeline.py           # 3 张 + 不推送
    python tests/test_daily_pipeline.py --full    # 6 张 + 推送
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.daily_pipeline import DailyPipeline  # noqa: E402


async def main(full: bool):
    print("=" * 60)
    print("  daily_pipeline 验收")
    print("=" * 60)

    pipe = DailyPipeline()

    # 1. 列预设
    print("\n[1] list_presets")
    r = await pipe.execute(action="list_presets")
    if r["status"] == "success":
        cats = r["result"]
        total = sum(len(v) for v in cats.values())
        print(f"    分类数: {len(cats)}  预设总数: {total}")

    # 2. 列主题
    print("\n[2] list_topics")
    r = await pipe.execute(action="list_topics")
    if r["status"] == "success":
        styles = r["result"]
        total = sum(len(v) for v in styles.values())
        print(f"    风格数: {len(styles)}  主题总数: {total}")

    # 3. 全流程（小规模）
    print(f"\n[3] run（{'完整 6 张' if full else '最小 3 张'}，不推送）")
    r = await pipe.execute(
        action="run",
        topic="月下松林",
        count=6 if full else 3,
        theme="newspaper",
        publish=False,
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    主题: {res['topic']}")
        print(f"    预设: {res['preset']}")
        print(f"    图片: {res['image_count']} 张 → {res['image_dir']}")
        print(f"    文章: {res['md_path']}")
        print(f"    排版: {res['article_dir']}")
        print(f"    预览: {res['preview_path']}")
        print(f"    推送: {res['published']} ({res['publish_error']})")
        print(f"    耗时: {res['elapsed']}")
    else:
        print(f"    错误: {r['error']}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="完整流程（6 张 + 推送）")
    args = parser.parse_args()
    asyncio.run(main(args.full))