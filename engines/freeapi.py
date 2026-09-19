# engines/freeapi.py
"""Free API 引擎（社区免费代理）。

无需注册，无需 API Key。
限流：约 10 秒 5 次，代码里用 2.5s 间隔保守处理。
"""

import asyncio
import base64
import io
import json
import random
import time
from typing import Optional

import requests
from PIL import Image

from .base import BaseEngine
from .registry import register


@register("freeapi")
class FreeAPIEngine(BaseEngine):
    CAPABILITIES = {"t2i"}

    DEFAULT_BASE_URL = "https://openai.good.hidns.vip/v1"
    DEFAULT_MODEL = "qwen3.7-plus"
    API_KEY = "https://github.com/smanx/free-api"

    SUPPORTED_SIZES = [
        "1024x1024", "1024x1792", "1792x1024",
        "1280x720", "720x1280",
    ]

    def __init__(self, model: str = "", base_url: str = ""):
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or self.DEFAULT_MODEL
        self.api_key = self.API_KEY
        self._timeout = 120
        self._min_interval = 2.5
        self._last_request = 0.0

    def _get_size(self, width: int, height: int) -> str:
        s = f"{width}x{height}"
        if s in self.SUPPORTED_SIZES:
            return s
        aspect = width / height
        best, best_diff = "1024x1024", float("inf")
        for s in self.SUPPORTED_SIZES:
            w, h = map(int, s.split("x"))
            d = abs(aspect - w / h)
            if d < best_diff:
                best_diff, best = d, s
        return best

    async def generate_single(
        self,
        prompt: str,
        negative: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        cfg: float = 7.5,
        seed: Optional[int] = None,
    ) -> Image.Image:
        return await asyncio.to_thread(
            self._generate_sync, prompt, negative, width, height, steps, cfg, seed,
        )

    def _generate_sync(self, prompt, negative, width, height, steps, cfg, seed):
        if seed is None:
            seed = random.randint(1, 2**31 - 1)

        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        size = self._get_size(width, height)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json",
        }
        if negative:
            data["negative_prompt"] = negative
        if seed:
            data["seed"] = seed
        if steps:
            data["steps"] = steps
        if cfg:
            data["guidance_scale"] = cfg

        url = f"{self.base_url}/images/generations"

        max_retries = 3
        last_err: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=self._timeout)
                self._last_request = time.time()

                if resp.status_code == 200:
                    result = resp.json()
                    item = result.get("data", [{}])[0]

                    b64 = item.get("b64_json")
                    if b64:
                        if b64.startswith("data:image"):
                            b64 = b64.split(",", 1)[1]
                        return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

                    img_url = item.get("url")
                    if img_url:
                        r = requests.get(img_url, timeout=30)
                        return Image.open(io.BytesIO(r.content)).convert("RGB")

                    raise RuntimeError(f"FreeAPI 无法解析图片: {json.dumps(result)[:200]}")

                if resp.status_code in (400, 429, 500, 502, 503, 504):
                    last_err = RuntimeError(f"FreeAPI HTTP {resp.status_code}: {resp.text[:200]}")
                    time.sleep(2 * attempt)
                    continue

                raise RuntimeError(f"FreeAPI HTTP {resp.status_code}: {resp.text[:200]}")

            except requests.exceptions.RequestException as e:
                last_err = e
                if attempt < max_retries:
                    time.sleep(2)
                    continue

        raise RuntimeError(f"FreeAPI 重试耗尽: {last_err}")

    def get_model(self) -> str:
        return self.model