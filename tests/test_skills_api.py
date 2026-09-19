#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Skills API 验收。

跑之前先起后端：
    python -m server.run
"""

import asyncio
import sys

import httpx

BASE = "http://127.0.0.1:8000"


async def main():
    print("=" * 60)
    print("  Skills API 验收")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BASE, timeout=180) as client:
        # 1. 列出 skills
        print("\n[1] GET /skills")
        r = await client.get("/api/v1/skills")
        r.raise_for_status()
        skills = r.json()
        print(f"    共 {len(skills)} 个 skill")
        for s in skills:
            print(f"    - {s['id']}: {s['name']} ({len(s['actions'])} actions)")

        # 2. voice / list_voices
        print("\n[2] POST /skills/voice_assistant/execute  action=list_voices")
        r = await client.post(
            "/api/v1/skills/voice_assistant/execute",
            json={"action": "list_voices", "params": {}},
        )
        r.raise_for_status()
        data = r.json()
        print(f"    状态: {data['status']}")
        print(f"    语音数: {data['result']['count']}")

        # 3. voice / tts
        print("\n[3] POST /skills/voice_assistant/execute  action=tts")
        r = await client.post(
            "/api/v1/skills/voice_assistant/execute",
            json={
                "action": "tts",
                "params": {
                    "text": "你好，这里是 PromptForge 的语音助手。",
                    "voice": "zh-CN-XiaoxiaoNeural",
                },
            },
        )
        r.raise_for_status()
        data = r.json()
        print(f"    状态: {data['status']}")
        if data["status"] == "success":
            url = data["result"].get("audio_path", "")
            print(f"    URL: {url}")

            # 4. 下载
            if url.startswith("/files/"):
                print(f"\n[4] GET {url}")
                r2 = await client.get(url)
                print(f"    下载 {len(r2.content)} bytes")

        # 5. music / list_options
        print("\n[5] POST /skills/music_generator/execute  action=list_options")
        r = await client.post(
            "/api/v1/skills/music_generator/execute",
            json={"action": "list_options", "params": {}},
        )
        r.raise_for_status()
        data = r.json()
        print(f"    情绪: {len(data['result']['emotions'])}")
        print(f"    编曲: {len(data['result']['arrangements'])}")

        # 6. music / compose_midi
        print("\n[6] POST /skills/music_generator/execute  action=compose_midi")
        r = await client.post(
            "/api/v1/skills/music_generator/execute",
            json={
                "action": "compose_midi",
                "params": {
                    "topic": "星辰大海",
                    "emotion": "epic",
                    "duration": 15,
                    "arrangement": "symphony",
                },
            },
        )
        r.raise_for_status()
        data = r.json()
        print(f"    状态: {data['status']}")
        if data["status"] == "success":
            url = data["result"].get("midi_path", "")
            print(f"    URL: {url}")

            if url.startswith("/files/"):
                print(f"\n[7] GET {url}")
                r2 = await client.get(url)
                print(f"    下载 {len(r2.content)} bytes")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())