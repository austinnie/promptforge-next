#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""news_aggregator 验收。

用法：
    python tests/test_news_aggregator.py
    python tests/test_news_aggregator.py --summary   # 带 AI 摘要
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.news_aggregator import NewsAggregator  # noqa: E402


async def main(with_summary: bool = False):
    print("=" * 60)
    print("  news_aggregator 验收")
    print("=" * 60)

    na = NewsAggregator()

    # 1. 列源
    print("\n[1] list_feeds")
    r = await na.execute(action="list_feeds")
    if r["status"] == "success":
        cats = r["result"]["categories"]
        print(f"    分类数: {len(cats)}")
        for c in cats:
            print(f"      {c['id']:10} {c['name']} ({c['feed_count']} 个源)")

    # 2. 抓科技新闻
    print("\n[2] fetch（category=tech，前 10 条）")
    r = await na.execute(
        action="fetch",
        category="tech",
        top_n=10,
        validate=True,
        with_summary=with_summary,
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    抓取: {res['total_fetched']} 条")
        print(f"    去重后: {res['unique_count']} 条")
        print(f"    展示: {res['display_count']} 条")
        print(f"    源数: {res['feeds_count']}")
        print(f"    耗时: {res['elapsed']}")
        print(f"    报告: {res['report_file']}")

        if res.get("summary"):
            print(f"\n    摘要引擎: {res['summary_engine']}")
            print(f"    摘要前 200 字:\n{res['summary'][:200]}...")

        print(f"\n    前 3 条新闻:")
        for i, art in enumerate(res["articles"][:3], 1):
            print(f"      {i}. [{art['source']}] {art['title'][:60]}")
    else:
        print(f"    错误: {r['error']}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true",
                        help="生成 AI 摘要（消耗 LLM）")
    args = parser.parse_args()
    asyncio.run(main(with_summary=args.summary))