# engines/mock.py
"""Mock 引擎：无需 API Key，直接返回一张图，用于离线测试。"""

import hashlib
from typing import Optional

from PIL import Image, ImageDraw

from .base import BaseEngine
from .registry import register


def _color_from_seed(seed: str) -> tuple[int, int, int]:
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return r, g, b


@register("mock")
class MockEngine(BaseEngine):
    CAPABILITIES = {"t2i", "i2i"}

    def __init__(self, **kwargs):
        # 忽略所有配置
        pass

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
        return self._render(prompt, width, height, seed)

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
        return self._render(prompt, width, height, seed)

    def _render(self, prompt: str, width: int, height: int, seed: Optional[int]) -> Image.Image:
        key = f"{prompt}|{seed}"
        c1 = _color_from_seed(key)
        c2 = _color_from_seed(key + "|bg")

        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        # 对角渐变
        for y in range(height):
            t = y / max(height - 1, 1)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 叠一层文字
        try:
            from PIL import ImageFont
            font = ImageFont.load_default()
        except Exception:
            font = None
        text = f"[MOCK]\n{prompt[:60]}"
        try:
            draw.multiline_text((20, 20), text, fill=(255, 255, 255), font=font)
        except Exception:
            pass

        return img