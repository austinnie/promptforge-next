#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""图生图 API 验收。

流程：
    1. 文生图拿一张底图（用 mock 引擎快）
    2. 读底图 → base64
    3. POST /jobs/image-to-image
    4. 轮询 → 下载结果

跑之前先起后端：
    python -m server.run
"""

import asyncio
import base64
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"


async def _poll(client, job_id, max_wait=120):
    for _ in range(int(max_wait * 2)):
        r = await client.get(f"/api/v1/jobs/{job_id}")
        j = r.json()
        if j["status"] in ("succeeded", "failed"):
            return j
        await asyncio.sleep(0.5)
    return {"status": "timeout", "message": "轮询超时"}


async def main():
    print("=" * 60)
    print("  图生图 API 验收")
    print("=" * 60)

    async with httpx.AsyncClient(base_url=BASE, timeout=300) as client:
        # 1. 文生图拿底图
        print("\n[1] 生成底图（mock 引擎）")
        r = await client.post("/api/v1/jobs/image", json={
            "prompt": "a mountain landscape, sunny day",
            "width": 512, "height": 512, "engine": "mock",
        })
        r.raise_for_status()
        jid = r.json()["id"]
        j = await _poll(client, jid)
        assert j["status"] == "succeeded", j
        img_url = j["result"]["url"]
        print(f"    底图 URL: {img_url}")

        # 2. 下载底图 → base64
        print("\n[2] 下载底图并转 base64")
        r = await client.get(img_url)
        assert r.status_code == 200
        b64 = base64.b64encode(r.content).decode("ascii")
        print(f"    原始: {len(r.content)} bytes → base64: {len(b64)} chars")

        # 3. 提交图生图
        print("\n[3] POST /jobs/image-to-image")
        r = await client.post("/api/v1/jobs/image-to-image", json={
            "prompt": "make it look like a Van Gogh oil painting",
            "image_base64": b64,
            "strength": 0.75,
            "width": 512,
            "height": 512,
        })
        r.raise_for_status()
        jid = r.json()["id"]
        print(f"    任务已创建: {jid}")

        # 4. 轮询
        print("\n[4] 轮询")
        j = await _poll(client, jid, max_wait=180)
        print(f"    状态: {j['status']} | 引擎: {j.get('result',{}).get('engine')}")
        if j["status"] != "succeeded":
            print(f"    错误: {j.get('error')}")
            return

        # 5. 下载结果
        print("\n[5] 下载结果")
        out_url = j["result"]["url"]
        r = await client.get(out_url)
        out_path = ROOT / "data" / "assets" / "test_i2i_result.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(r.content)
        print(f"    保存: {out_path.relative_to(ROOT)} ({len(r.content) // 1024} KB)")
        print(f"    尺寸: {j['result']['width']}x{j['result']['height']}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())