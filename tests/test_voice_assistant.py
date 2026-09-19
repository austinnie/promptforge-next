#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""voice_assistant 验收。

用法：
    python tests/test_voice_assistant.py
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.voice_assistant import VoiceAssistant  # noqa: E402


async def main():
    print("=" * 60)
    print("  voice_assistant 验收")
    print("=" * 60)

    va = VoiceAssistant()

    # 1. 列语音
    print("\n[1] list_voices")
    r = await va.execute(action="list_voices")
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        print(f"    语音数: {r['result']['count']}")
        print(f"    默认: {r['result']['default']}")

    # 2. 短文本 TTS
    print("\n[2] TTS（短文本）")
    r = await va.execute(
        action="tts",
        text="你好，这里是 PromptForge。",
        voice="zh-CN-XiaoxiaoNeural",
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    音频: {res['audio_path']}")
        print(f"    时长: {res['duration']}s")
    else:
        print(f"    错误: {r.get('error')}")

    # 3. 长文本 TTS（自动分段）
    print("\n[3] TTS（长文本，自动分段）")
    long_text = "这是第一句话。" * 300   # 约 2400 字
    r = await va.execute(
        action="tts",
        text=long_text,
        voice="zh-CN-XiaoxiaoNeural",
        speed=1.1,
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    分段数: {res.get('chunks')}")
        print(f"    主文件: {res.get('audio_path') or '(无合并，看 segment_files)'}")
        if res.get("segment_files"):
            print(f"    分段文件: {len(res['segment_files'])} 个")
    else:
        print(f"    错误: {r.get('error')}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())