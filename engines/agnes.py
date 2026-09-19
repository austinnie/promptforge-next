# engines/agnes.py
"""Agnes AI 图像引擎。"""

import asyncio
import io
import json
import random
import re
import time
from typing import Optional

import requests
from PIL import Image

from .base import BaseEngine
from .registry import register


@register("agnes")
class AgnesEngine(BaseEngine):
    CAPABILITIES = {"t2i", "i2i"}

    ROUTES = [
        "https://apihub.agnes-ai.com/v1",
        "https://apihub.agnes-ai.cn/v1",
        "https://api.agnes-ai.cn/v1",
    ]

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        image_model: str = "agnes-image-2.1-flash",
    ):
        self.api_key = api_key
        self.base_url = base_url or self.ROUTES[0]
        self.image_model = image_model
        self._timeout = 180
        self._min_interval = 0.5
        self._last_request = 0.0

        if not self.api_key:
            raise ValueError("Agnes 需要 AGNES_API_KEY")

    def _to_size_tier(self, width: int, height: int) -> str:
        max_edge = max(width, height)
        if max_edge <= 1024:
            return "1K"
        if max_edge <= 2048:
            return "2K"
        if max_edge <= 3072:
            return "3K"
        return "4K"

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
            seed = random.randint(0, 999)
        else:
            seed = max(-1, min(999, seed))

        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        size = self._to_size_tier(width, height)
        data = {
            "model": self.image_model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "url",
            "seed": seed,
        }

        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        resp = requests.post(url, headers=headers, json=data, timeout=self._timeout)
        self._last_request = time.time()

        if resp.status_code != 200:
            raise RuntimeError(f"Agnes HTTP {resp.status_code}: {resp.text[:200]}")

        result = resp.json()

        image_url = None
        if result.get("data"):
            image_url = result["data"][0].get("url")
        if not image_url and result.get("output"):
            out = result["output"]
            if out.get("results"):
                image_url = out["results"][0].get("url")
            elif out.get("image_url"):
                image_url = out["image_url"]

        if not image_url:
            raise RuntimeError(f"Agnes 未返回图片: {json.dumps(result)[:200]}")

        if image_url.startswith("data:image"):
            b64 = re.sub(r"^data:image/.+;base64,", "", image_url)
            import base64
            return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")

        img_resp = requests.get(image_url, timeout=60)
        return Image.open(io.BytesIO(img_resp.content)).convert("RGB")

    async def image_to_image(
        self,
        prompt: str,
        image: Image.Image,
        strength: float = 0.7,
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        cfg: float = 7.5,
        seed: Optional[int] = None,
    ) -> Image.Image:
        return await asyncio.to_thread(
            self._img2img_sync, prompt, image, width, height, seed,
        )

    def _img2img_sync(self, prompt, image, width, height, seed):
        import base64

        if seed is None:
            seed = random.randint(0, 999)
        else:
            seed = max(-1, min(999, seed))

        if max(image.size) > 1024:
            scale = 1024 / max(image.size)
            image = image.resize(
                (int(image.size[0] * scale), int(image.size[1] * scale)),
                Image.Resampling.LANCZOS,
            )

        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")

        data = {
            "model": self.image_model,
            "prompt": prompt,
            "n": 1,
            "size": self._to_size_tier(width, height),
            "seed": seed,
            "extra_body": {
                "image": [f"data:image/png;base64,{b64}"],
                "response_format": "url",
            },
        }

        url = f"{self.base_url.rstrip('/')}/images/generations"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(url, headers=headers, json=data, timeout=self._timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Agnes i2i HTTP {resp.status_code}: {resp.text[:200]}")

        result = resp.json()
        image_url = None
        if result.get("data"):
            image_url = result["data"][0].get("url")
        if not image_url:
            raise RuntimeError(f"Agnes i2i 未返回图片: {json.dumps(result)[:200]}")

        img_resp = requests.get(image_url, timeout=60)
        return Image.open(io.BytesIO(img_resp.content)).convert("RGB")

    def get_model(self) -> str:
        return self.image_model