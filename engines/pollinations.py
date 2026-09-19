# engines/pollinations.py
"""Pollinations AI 引擎（异步版）。

统一网关：https://gen.pollinations.ai
能力：t2i / i2i / chat / vision / audio / video
特性：中文 prompt 自动翻译、prompt 自动清理、429 指数退避
"""

import asyncio
import base64
import io
import random
import time
import urllib.parse
from typing import Dict, List, Optional, Union

import requests
from PIL import Image

from .base import BaseEngine
from .registry import register


@register("pollinations")
class PollinationsEngine(BaseEngine):
    CAPABILITIES = {"t2i", "i2i", "chat", "vision", "audio", "video"}

    BASE_URL = "https://gen.pollinations.ai"

    # ✅ 使用免费社区模型（避免 API key 权限限制）
    DEFAULT_MODELS = {
        "t2i": "black-forest-labs/flux.1-schnell",
        "i2i": "black-forest-labs/flux.1-kontext-pro",
        "chat": "community/NamanSoni78/gemini-3.8-flash",
        "vision": "community/NamanSoni78/gemini-3.8-flash",
        "audio": "community/NamanSoni78/aura-2-amalthea-en",
        "video": "veo",
    }

    def __init__(
        self,
        api_key: str = "",
        model: str = "",
        image_model: str = "",
        video_model: str = "",
        audio_model: str = "",
    ):
        self.api_key = api_key
        self.image_model = image_model or model or self.DEFAULT_MODELS["t2i"]
        self.video_model = video_model or self.DEFAULT_MODELS["video"]
        self.audio_model = audio_model or self.DEFAULT_MODELS["audio"]

        self._timeout = 180
        self._min_interval = 0.5
        self._last_request = 0.0
        self._max_retries = 3
        self._retry_delay = 2

    # ==================== 内部：请求 ====================

    def _headers(self) -> Dict[str, str]:
        h = {"User-Agent": "PromptForge-Next/0.1"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict | None = None,
        data: dict | None = None,
        timeout: int = 120,
    ) -> requests.Response:
        self._rate_limit()
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = self._headers()

        for attempt in range(self._max_retries):
            try:
                resp = requests.request(
                    method=method, url=url, headers=headers,
                    params=params, json=data, timeout=timeout,
                )
                if resp.status_code == 429:
                    wait = self._retry_delay * (2 ** attempt)
                    time.sleep(wait)
                    continue
                if resp.status_code >= 500:
                    if attempt < self._max_retries - 1:
                        time.sleep(self._retry_delay)
                        continue
                    raise RuntimeError(f"Pollinations {resp.status_code}: {resp.text[:200]}")
                if resp.status_code != 200:
                    raise RuntimeError(f"Pollinations {resp.status_code}: {resp.text[:200]}")
                return resp
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay)
                    continue
                raise
        raise RuntimeError("Pollinations 所有重试已用尽")

    # ==================== 中文翻译 + prompt 清理 ====================

    @staticmethod
    def _has_chinese(s: str) -> bool:
        return any('\u4e00' <= c <= '\u9fff' for c in s)

    def _translate_zh_to_en(self, text: str) -> str:
        try:
            instruction = (
                "Translate the following Chinese prompt into concise English "
                "for a text-to-image model. Keep all visual details. "
                "Output ONLY the English translation.\n\n"
                f"Chinese: {text}"
            )
            encoded = urllib.parse.quote(instruction)
            resp = requests.get(
                f"{self.BASE_URL}/text/{encoded}",
                params={"model": "openai-fast"},
                timeout=20,
                headers=self._headers(),
            )
            if resp.status_code == 200:
                translated = resp.text.strip().strip('"').strip("'")
                if translated and len(translated) > 3:
                    return translated
        except Exception:
            pass
        return text

    def _clean_prompt(self, prompt: str) -> str:
        clean = prompt.strip()
        for word in ["生成图片", "生成一张", "生成", "帮我画", "画一张", "画"]:
            clean = clean.replace(word, "")
        clean = clean.strip("，,。.：: ")
        if not clean:
            return clean

        if self._has_chinese(clean):
            clean = self._translate_zh_to_en(clean)

        low = clean.lower()
        has_q = any(q in low for q in (
            "masterpiece", "best quality", "highly detailed",
            "8k", "ultra detailed", "professional photography",
        ))
        if not has_q:
            prefix = "masterpiece, best quality, highly detailed, sharp focus"
            suffix = "professional photography, cinematic lighting, 8k uhd, intricate details"
            clean = f"{prefix}, {clean}, {suffix}"

        parts = [p.strip() for p in clean.split(",") if p.strip()]
        seen = set()
        unique = []
        for p in parts:
            k = p.lower()
            if k not in seen:
                seen.add(k)
                unique.append(p)
        result = ", ".join(unique)
        if len(result) > 500:
            result = result[:500].rsplit(",", 1)[0]
        return result

    # ==================== 图片工具 ====================

    @staticmethod
    def _img_to_b64(img: Image.Image) -> str:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def _img_to_data_uri(self, img: Image.Image) -> str:
        return f"data:image/png;base64,{self._img_to_b64(img)}"

    @staticmethod
    def _resize(img: Image.Image, max_size: int = 1024) -> Image.Image:
        w, h = img.size
        if max(w, h) <= max_size:
            return img
        s = max_size / max(w, h)
        nw = ((int(w * s) + 7) // 8) * 8
        nh = ((int(h * s) + 7) // 8) * 8
        return img.resize((nw, nh), Image.Resampling.LANCZOS)

    @staticmethod
    def _download(url: str) -> Image.Image:
        if url.startswith("data:image"):
            b64 = url.split(",", 1)[1]
            return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        resp = requests.get(url, timeout=60)
        return Image.open(io.BytesIO(resp.content)).convert("RGB")

    # ==================== t2i ====================

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
            self._t2i_sync, prompt, negative, width, height, steps, cfg, seed,
        )

    def _t2i_sync(self, prompt, negative, width, height, steps, cfg, seed):
        if seed is None:
            seed = random.randint(1, 2**31 - 1)
        clean = self._clean_prompt(prompt)
        encoded = urllib.parse.quote(clean)
        params = {
            "model": self.image_model,
            "width": width,
            "height": height,
            "seed": seed,
            "nologo": "true",
        }
        if negative and len(negative) < 100:
            params["negative"] = negative
        if steps:
            params["steps"] = steps
        if cfg:
            params["cfg"] = cfg

        resp = self._request(
            "GET", f"/image/{encoded}", params=params, timeout=self._timeout,
        )
        img = Image.open(io.BytesIO(resp.content)).convert("RGB")
        if img.size[0] < 10 or img.size[1] < 10:
            raise RuntimeError("Pollinations 返回图片尺寸异常")
        return img

    # ==================== i2i ====================

    async def image_to_image(
        self,
        prompt: str,
        image: Union[Image.Image, List[Image.Image], str],
        strength: float = 0.7,
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        cfg: float = 7.5,
        seed: Optional[int] = None,
    ) -> Image.Image:
        return await asyncio.to_thread(
            self._i2i_sync, prompt, image, strength, width, height, seed,
        )

    def _i2i_sync(self, prompt, image, strength, width, height, seed):
        uris: List[str] = []
        if isinstance(image, str):
            uris = [image]
        elif isinstance(image, list):
            for img in image:
                if isinstance(img, str):
                    uris.append(img)
                elif isinstance(img, Image.Image):
                    uris.append(self._img_to_data_uri(self._resize(img, 1024)))
        elif isinstance(image, Image.Image):
            uris = [self._img_to_data_uri(self._resize(image, 1024))]

        if not uris:
            raise ValueError("Pollinations i2i 需要至少一张参考图")

        if seed is None:
            seed = random.randint(1, 2**31 - 1)
        clean = self._clean_prompt(prompt)

        data = {
            "model": self.DEFAULT_MODELS["i2i"],
            "prompt": clean,
            "image": uris,
            "n": 1,
            "size": f"{width}x{height}",
            "response_format": "b64_json",
            "seed": seed,
        }
        if strength and 0 < strength < 1:
            data["strength"] = strength

        resp = self._request("POST", "/v1/images/edits", data=data, timeout=300)
        result = resp.json()
        item = result.get("data", [{}])[0]
        b64 = item.get("b64_json")
        if b64:
            if b64.startswith("data:image"):
                b64 = b64.split(",", 1)[1]
            return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        url = item.get("url")
        if url:
            return self._download(url)
        raise RuntimeError(f"Pollinations i2i 解析失败: {str(result)[:200]}")

    # ==================== chat ====================

    async def chat(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(
            self._chat_sync, messages, temperature, max_tokens,
        )

    def _chat_sync(self, messages, temperature, max_tokens) -> str:
        data = {
            "model": self.DEFAULT_MODELS["chat"],     # ✅ 从常量读，不硬编码
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = self._request("POST", "/v1/chat/completions", data=data, timeout=120)
        result = resp.json()
        if result.get("choices"):
            return result["choices"][0].get("message", {}).get("content", "")
        raise RuntimeError(f"Pollinations chat 解析失败: {str(result)[:200]}")

    # ==================== vision ====================

    async def image_to_text(
        self,
        image: Image.Image,
        prompt: str = "描述这张图",
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(self._vision_sync, image, prompt)

    def _vision_sync(self, image, prompt) -> str:
        uri = self._img_to_data_uri(self._resize(image, 1024))
        messages = [
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": uri}},
            ]}
        ]
        return self._chat_sync(messages, 0.7, 512)

    # ==================== audio ====================

    async def generate_audio(
        self,
        text: str,
        voice: str = "alloy",
        output_format: str = "mp3",
        **kwargs,
    ) -> bytes:
        return await asyncio.to_thread(
            self._audio_sync, text, voice, output_format,
        )

    def _audio_sync(self, text, voice, output_format) -> bytes:
        data = {
            "model": self.audio_model,
            "input": text,
            "voice": voice,
            "response_format": output_format,
        }
        resp = self._request("POST", "/v1/audio/speech", data=data, timeout=180)
        return resp.content

    # ==================== video ====================

    async def video_generation(self, prompt: str, **kwargs) -> dict:
        return await asyncio.to_thread(self._video_sync, prompt, **kwargs)

    def _video_sync(self, prompt, image=None, duration: int = 5,
                    width: int = 768, height: int = 768, **kwargs) -> dict:
        if width == height:
            ar = "1:1"
        elif width > height:
            ar = "16:9"
        else:
            ar = "9:16"

        clean = self._clean_prompt(prompt)
        encoded = urllib.parse.quote(clean)
        params = {
            "model": self.video_model,
            "duration": duration,
            "aspectRatio": ar,
            "seed": random.randint(1, 2**31 - 1),
        }
        if image is not None:
            if isinstance(image, Image.Image):
                params["image"] = self._img_to_data_uri(self._resize(image, 1024))
            elif isinstance(image, str):
                params["image"] = image

        timeout = max(300, duration * 30)
        resp = self._request("GET", f"/video/{encoded}", params=params, timeout=timeout)
        video_bytes = resp.content
        if len(video_bytes) < 1000:
            raise RuntimeError(f"Pollinations 视频数据异常 ({len(video_bytes)} 字节)")

        return {
            "video_bytes": video_bytes,
            "status": "completed",
            "progress": 100,
            "_sync": True,
        }

    # ==================== 元信息 ====================

    def get_model(self) -> str:
        return self.image_model