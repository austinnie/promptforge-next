#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""video_generator 验收。

默认只生成单段 5 秒视频（快，约 30-60 秒）。
--long 跑 30 秒长视频（约 3-5 分钟，会限流冷却）。

用法：
    python tests/test_video_generator.py
    python tests/test_video_generator.py --long
"""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.video_generator import VideoGenerator  # noqa: E402


async def main(long: bool):
    print("=" * 60)
    print("  video_generator 验收")
    print("=" * 60)

    vg = VideoGenerator()

    if long:
        print("\n[1] 长视频（30s = 3 段 × 10s，含冷却）")
        r = await vg.execute(
            action="generate",
            prompt="a serene mountain lake at sunrise, slow camera pan",
            duration=30,
            segment_duration=10,
            width=768,
            height=768,
            auto_merge=True,
        )
    else:
        print("\n[1] 单段视频（5s）")
        r = await vg.execute(
            action="generate",
            prompt="a serene mountain lake at sunrise, slow camera pan",
            duration=5,
            width=768,
            height=768,
        )

    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    引擎: {res.get('engine')}")
        print(f"    时长: {res.get('duration')}s")
        print(f"    片段: {res.get('segments')}")
        print(f"    大小: {res.get('size_bytes', 0) // 1024} KB")
        if res.get("video_path"):
            print(f"    URL: {res['video_url']}")
        if res.get("video_paths"):
            print(f"    分段数: {len(res['video_paths'])}")
            print(f"    警告: {res.get('warning')}")
        print(f"    耗时: {res.get('elapsed')}")
    else:
        print(f"    错误: {r['error']}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--long", action="store_true",
                        help="跑 30 秒长视频（含分段+冷却）")
    args = parser.parse_args()
    asyncio.run(main(args.long))