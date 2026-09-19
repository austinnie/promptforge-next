# engines/openrouter.py
"""OpenRouter 引擎（图像）。"""

import asyncio
import base64
import io
import random
from typing import Optional

import requests
from PIL import Image

from .base import BaseEngine
from .registry import register


@register("openrouter")
class OpenRouterEngine(BaseEngine):
    CAPABILITIES = {"t2i"}

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str = "",
        model: str = "bytedance-seed/seedream-4.5",
    ):
        if not api_key:
            raise ValueError("OpenRouter 需要 OPENROUTER_API_KEY")
        self.api_key = api_key
        self.model = model
        self._timeout = 180

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
            self._generate_sync, prompt, width, height, seed,
        )

    def _generate_sync(self, prompt, width, height, seed):
        if seed is None:
            seed = random.randint(1, 2**31 - 1)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://promptforge.local",
            "X-Title": "PromptForge-Next",
        }
        data = {
            "model": self.model,
            "prompt": prompt,
            "n": 1,
            "size": f"{width}x{height}",
            "response_format": "b64_json",
            "seed": seed,
        }

        resp = requests.post(
            f"{self.BASE_URL}/images/generations",
            headers=headers, json=data, timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter HTTP {resp.status_code}: {resp.text[:200]}")

        result = resp.json()
        item = result["data"][0]

        b64 = item.get("b64_json")
        if b64:
            if b64.startswith("data:image"):
                b64 = b64.split(",", 1)[1]
            return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

        img_url = item.get("url")
        if img_url:
            img_resp = requests.get(img_url, timeout=60)
            return Image.open(io.BytesIO(img_resp.content)).convert("RGB")

        raise RuntimeError(f"OpenRouter 无法解析图片: {str(result)[:200]}")

    def get_model(self) -> str:
        return self.model