# engines/pollinations.py
"""Pollinations AI 引擎（图像）。"""

import asyncio
import io
import random
import urllib.parse
from typing import Optional

import requests
from PIL import Image

from .base import BaseEngine
from .registry import register


@register("pollinations")
class PollinationsEngine(BaseEngine):
    CAPABILITIES = {"t2i"}

    BASE_URL = "https://gen.pollinations.ai"

    def __init__(
        self,
        api_key: str = "",
        model: str = "black-forest-labs/flux.1-schnell",
    ):
        self.api_key = api_key
        self.model = model
        self._timeout = 180
        if not self.api_key:
            print("⚠️ Pollinations: 未设置 POLLINATIONS_API_KEY，部分模型可能受限")

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

        encoded = urllib.parse.quote(prompt)
        url = f"{self.BASE_URL}/image/{encoded}"

        params = {
            "model": self.model,
            "width": width,
            "height": height,
            "seed": seed,
            "nologo": "true",
        }
        if negative and len(negative) < 100:
            params["negative"] = negative

        headers = {"User-Agent": "PromptForge-Next/0.1"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        resp = requests.get(url, params=params, headers=headers, timeout=self._timeout)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Pollinations HTTP {resp.status_code}: {resp.text[:200]}"
            )

        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        if img.size[0] < 10 or img.size[1] < 10:
            raise RuntimeError("Pollinations 返回的图片尺寸异常")
        return img

    def get_model(self) -> str:
        return self.model