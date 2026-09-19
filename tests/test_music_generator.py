#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""music_generator 验收。

用法：
    python tests/test_music_generator.py
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.music_generator import MusicMaestro  # noqa: E402


async def main():
    print("=" * 60)
    print("  music_generator 验收")
    print("=" * 60)

    mm = MusicMaestro()

    # 1. 列选项
    print("\n[1] list_options")
    r = await mm.execute(action="list_options")
    if r["status"] == "success":
        res = r["result"]
        print(f"    情绪: {len(res['emotions'])}")
        print(f"    编曲: {len(res['arrangements'])}")
        print(f"    乐器: {len(res['instruments'])}")

    # 2. 生成 MIDI（交响乐）
    print("\n[2] 交响乐 MIDI")
    r = await mm.execute(
        action="compose_midi",
        topic="星辰大海",
        emotion="epic",
        duration=15,
        arrangement="symphony",
        complexity=2,
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    MIDI: {res['midi_path']}")
        print(f"    大小: {res['size_bytes']} bytes")
        print(f"    乐器数: {res['tracks']}")
    else:
        print(f"    错误: {r.get('error')}")

    # 3. 生成 MIDI（中国风）+ 歌词
    print("\n[3] 中国风 MIDI + 歌词")
    r = await mm.execute(
        action="compose_midi",
        topic="月下独酌",
        emotion="romantic",
        duration=20,
        arrangement="chinese",
        with_lyrics=True,
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    MIDI: {res['midi_path']}")
        if res.get("lyrics"):
            print(f"    歌词标题: {res['lyrics'].get('title')}")
            print(f"    歌词引擎: {res.get('lyrics_engine')}")
    else:
        print(f"    错误: {r.get('error')}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())