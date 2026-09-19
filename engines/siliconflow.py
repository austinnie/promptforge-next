# engines/siliconflow.py
"""硅基流动（SiliconFlow）引擎。"""

import asyncio
import io
import random
from typing import Optional

import requests
from PIL import Image

from .base import BaseEngine
from .registry import register


@register("siliconflow")
class SiliconFlowEngine(BaseEngine):
    CAPABILITIES = {"t2i"}

    BASE_URL = "https://api.siliconflow.cn/v1"

    def __init__(self, api_key: str = "", model: str = "sd-turbo"):
        if not api_key:
            raise ValueError("SiliconFlow 需要 SILICONFLOW_API_KEY")
        self.api_key = api_key
        self.model = model
        self._timeout = 180

    def _size(self, width: int, height: int) -> str:
        if "turbo" in self.model and "sdxl" not in self.model:
            return "512x512"
        if width == height:
            return "1024x1024"
        if width > height:
            return "1024x768"
        return "768x1024"

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
            self._generate_sync, prompt, negative, width, height, seed,
        )

    def _generate_sync(self, prompt, negative, width, height, seed):
        if seed is None:
            seed = random.randint(1, 2**31 - 1)

        data = {
            "model": self.model,
            "prompt": prompt,
            "image_size": self._size(width, height),
            "seed": seed,
        }
        if negative:
            data["negative_prompt"] = negative

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            f"{self.BASE_URL}/images/generations",
            headers=headers, json=data, timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"SiliconFlow HTTP {resp.status_code}: {resp.text[:200]}")

        result = resp.json()
        img_url = result["data"][0].get("url")
        if not img_url:
            raise RuntimeError(f"SiliconFlow 未返回图片: {str(result)[:200]}")

        img_resp = requests.get(img_url, timeout=60)
        return Image.open(io.BytesIO(img_resp.content)).convert("RGB")

    def get_model(self) -> str:
        return self.model