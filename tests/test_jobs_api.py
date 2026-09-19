#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""jobs API 验收：image / video / audio / chat。

跑之前先起后端：
    python -m server.run
"""

import asyncio
import sys

import httpx

BASE = "http://127.0.0.1:8000"


async def _poll(client, job_id, max_wait=120):
    for _ in range(int(max_wait * 2)):
        r = await client.get(f"/api/v1/jobs/{job_id}")
        j = r.json()
        if j["status"] in ("succeeded", "failed"):
            return j
        await asyncio.sleep(0.5)
    return {"status": "timeout", "message": "轮询超时"}


async def main(video: bool = False):
    print("=" * 60)
    print("  jobs API 验收")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BASE, timeout=600) as client:
        # 1. 图片
        print("\n[1] POST /jobs/image")
        r = await client.post("/api/v1/jobs/image", json={
            "prompt": "a serene mountain lake at dawn",
            "width": 512, "height": 512, "engine": "mock",
        })
        r.raise_for_status()
        jid = r.json()["id"]
        j = await _poll(client, jid, max_wait=60)
        print(f"    状态: {j['status']} | 引擎: {j.get('result',{}).get('engine')}")

        # 2. 对话
        print("\n[2] POST /jobs/chat")
        r = await client.post("/api/v1/jobs/chat", json={
            "messages": [{"role": "user", "content": "用一句话描述'秋日'"}],
            "max_tokens": 100,
        })
        r.raise_for_status()
        data = r.json()
        print(f"    引擎: {data['engine']}")
        print(f"    文本: {data['text'][:80]}")

        # 3. 音频（TTS）
        print("\n[3] POST /jobs/audio")
        r = await client.post("/api/v1/jobs/audio", json={
            "text": "你好，这里是 PromptForge 测试。",
            "voice": "alloy",
        })
        r.raise_for_status()
        jid = r.json()["id"]
        j = await _poll(client, jid, max_wait=120)
        print(f"    状态: {j['status']} | 引擎: {j.get('result',{}).get('engine')}")
        if j["status"] == "succeeded":
            print(f"    URL: {j['result']['url']}")

        # 4. 视频（耗时长，可选）
        if video:
            print("\n[4] POST /jobs/video")
            r = await client.post("/api/v1/jobs/video", json={
                "prompt": "a calm mountain lake at sunrise, slow pan",
                "duration": 5,
                "width": 768, "height": 768,
            })
            r.raise_for_status()
            jid = r.json()["id"]
            j = await _poll(client, jid, max_wait=300)
            print(f"    状态: {j['status']} | 引擎: {j.get('result',{}).get('engine')}")
            if j["status"] == "succeeded":
                print(f"    URL: {j['result']['url']}")
                print(f"    大小: {j['result']['size_bytes'] // 1024} KB")
        else:
            print("\n[4] POST /jobs/video（跳过，加 --video 开启）")

        # 5. 任务列表
        print("\n[5] GET /jobs")
        r = await client.get("/api/v1/jobs?limit=20")
        r.raise_for_status()
        print(f"    共 {len(r.json())} 条")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", action="store_true",
                        help="跑视频生成（耗时 1-3 分钟）")
    args = parser.parse_args()
    asyncio.run(main(video=args.video))