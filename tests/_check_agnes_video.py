#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直连 Agnes /videos 端点，打印原始响应，定位 401 根因。"""

import os
import sys
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 手动读 .env
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.getenv("AGNES_API_KEY", "")
BASE_URL = os.getenv("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
VIDEO_MODEL = os.getenv("AGNES_VIDEO_MODEL", "agnes-video-2.5-flash")

print("=" * 60)
print("Agnes /videos 直连诊断")
print("=" * 60)
print(f"BASE_URL   : {BASE_URL}")
print(f"VIDEO_MODEL: {VIDEO_MODEL}")
print(f"API_KEY    : {API_KEY[:8]}...{API_KEY[-4:]}" if len(API_KEY) > 12 else f"API_KEY: {API_KEY!r}")
print()

if not API_KEY:
    print("❌ AGNES_API_KEY 未配置")
    sys.exit(1)

# ---- 1. 先测一个已知能通的端点 /chat/completions ----
print("[1] 测 /chat/completions（应该通）")
r = requests.post(
    f"{BASE_URL.rstrip('/')}/chat/completions",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json={
        "model": os.getenv("AGNES_TEXT_MODEL", "agnes-2.5-flash"),
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 5,
    },
    timeout=30,
)
print(f"    HTTP {r.status_code}")
print(f"    body: {r.text[:200]}")
print()

# ---- 2. 再测 /videos ----
print("[2] 测 /videos（当前报 401）")
data = {
    "model": VIDEO_MODEL,
    "prompt": "a cat walking on the beach",
    "seconds": "5",
    "mode": "text",
    "size": "720P",
    "aspect_ratio": "1:1",
}
print(f"    请求体: {json.dumps(data, ensure_ascii=False)}")
r = requests.post(
    f"{BASE_URL.rstrip('/')}/videos",
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json=data,
    timeout=60,
)
print(f"    HTTP {r.status_code}")
print(f"    body: {r.text[:500]}")
print()

# ---- 3. 换备用路由再试一次 ----
for alt in [
    "https://apihub.agnes-ai.cn/v1",
    "https://api.agnes-ai.cn/v1",
]:
    if alt == BASE_URL.rstrip("/"):
        continue
    print(f"[3] 备用路由: {alt}")
    try:
        r = requests.post(
            f"{alt}/videos",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json=data,
            timeout=60,
        )
        print(f"    HTTP {r.status_code}")
        print(f"    body: {r.text[:300]}")
    except Exception as e:
        print(f"    异常: {e}")
    print()

print("=" * 60)
print("完成。把上面完整输出贴过来。")
print("=" * 60)