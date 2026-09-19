#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P3 验收：起服务 → 创建任务 → 轮询 → 下载图片。

跑之前先在另一个终端执行：
    python -m server.run
"""

import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"


async def main():
    print("=" * 60)
    print("  P3 验收 - server")
    print("=" * 60)
    print()

    async with httpx.AsyncClient(base_url=BASE, timeout=180) as client:
        # 1. system
        r = await client.get("/api/v1/system/info")
        r.raise_for_status()
        info = r.json()
        print(f"[1] system: v{info['version']} @ {info['host']}:{info['port']}")
        print(f"    local_ip = {info['local_ip']}")
        print()

        # 2. engines
        r = await client.get("/api/v1/engines")
        engines = r.json()
        print(f"[2] engines: {len(engines)} 个")
        for n, i in engines.items():
            mark = "✅" if i["configured"] else "⬜"
            print(f"    {mark} {n:15} caps={i['capabilities']}")
        print()

        # 3. presets
        r = await client.get("/api/v1/presets")
        presets = r.json()
        total = sum(len(v) for v in presets.values())
        print(f"[3] presets: {total} 个，分类: {list(presets.keys())}")
        print()

        # 4. 创建任务（用 mock 保证可复现，避免真调 API）
        r = await client.post("/api/v1/jobs/image", json={
            "prompt": "月光下的森林，机甲少女背影",
            "width": 512,
            "height": 512,
            "engine": "mock",
        })
        assert r.status_code == 202, r.text
        job_id = r.json()["job_id"]
        print(f"[4] 任务已创建: {job_id}")
        print()

        # 5. 轮询
        print("[5] 轮询任务状态")
        last_status = None
        for _ in range(60):
            r = await client.get(f"/api/v1/jobs/{job_id}")
            j = r.json()
            if j["status"] != last_status or j["progress"] % 20 == 0:
                print(f"    {j['status']:10} {j['progress']:3}%  {j['message']}")
                last_status = j["status"]
            if j["status"] in ("succeeded", "failed"):
                break
            await asyncio.sleep(0.5)

        assert j["status"] == "succeeded", f"任务失败: {j}"
        url = j["result"]["url"]
        print(f"    图片 URL: {url}")
        print(f"    引擎: {j['result']['engine']}")
        print()

        # 6. 下载图片
        r = await client.get(url)
        assert r.status_code == 200
        out = ROOT / "data" / "assets" / "test_server_downloaded.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(r.content)
        print(f"[6] 已下载: {out.relative_to(ROOT)} ({len(r.content) // 1024} KB)")
        print()

        # 7. 列表
        r = await client.get("/api/v1/jobs")
        jobs = r.json()
        print(f"[7] 任务列表: {len(jobs)} 个")
        print()

    print("=" * 60)
    print("  🎉 P3 验收通过")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())