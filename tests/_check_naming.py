#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证文件名是否带 prompt 摘要。"""

import asyncio
import httpx

BASE = "http://127.0.0.1:8000"


async def main():
    async with httpx.AsyncClient(base_url=BASE, timeout=60) as c:
        r = await c.post("/api/v1/jobs/image", json={
            "prompt": "月光下的森林", "width": 512, "height": 512,
            "engine": "mock",
        })
        r.raise_for_status()
        jid = r.json()["id"]

        for _ in range(30):
            j = (await c.get(f"/api/v1/jobs/{jid}")).json()
            if j["status"] in ("succeeded", "failed"):
                break
            await asyncio.sleep(0.5)

        print(f"状态: {j['status']}")
        if j["status"] == "succeeded":
            print(f"URL: {j['result']['url']}")
        else:
            print(f"错误: {j.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())