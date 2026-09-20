# engines/agnes.py
"""Agnes AI 引擎（异步版）。

能力：t2i / i2i（多图）/ chat / vision / video / audio
特性：多路由自动 fallback（.com → .cn → api.cn）
"""

import asyncio
import base64
import io
import json
import random
import re
import time
from typing import List, Optional, Union

import requests
from PIL import Image

from .base import BaseEngine
from .registry import register
import logging 
logger = logging.getLogger(__name__)   # ← 新增

@register("agnes")
class AgnesEngine(BaseEngine):
    CAPABILITIES = {"t2i", "i2i", "chat", "vision", "video", "audio"}

    #ROUTES = [
    #    "https://apihub.agnes-ai.com/v1",
    #    "https://apihub.agnes-ai.cn/v1",
    #    "https://api.agnes-ai.cn/v1",
    #]
    ROUTES = [
        "https://apihub.agnes-ai.com/v1",
    ]    

    DEFAULT_MODELS = {
        "t2i": "agnes-image-2.1-flash",
        "i2i": "agnes-image-2.1-flash",
        "chat": "agnes-2.5-flash",
        "video": "agnes-video-2.5-flash",
        "vision": "agnes-2.5-flash",
        "audio": "agnes-audio-2.5-flash",
    }

    # audio 端点探测顺序（首次成功后缓存）
    AUDIO_ENDPOINTS = [
        "audio/speech",         # OpenAI TTS 兼容
        "music/generations",    # Agnes 音乐端点
        "audio/generations",    # 备用
    ]

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        image_model: str = "",
        text_model: str = "",
        video_model: str = "",
        vision_model: str = "",
        audio_model: str = "",
    ):
        if not api_key:
            raise ValueError("Agnes 需要 AGNES_API_KEY")

        self.api_key = api_key
        self._routes = list(self.ROUTES)
        if base_url:
            base = base_url.rstrip("/")
            self._routes = [base] + [r for r in self.ROUTES if r != base]
        self._route_index = 0
        self._failed_routes: set = set()

        self.image_model = image_model or self.DEFAULT_MODELS["t2i"]
        self.text_model = text_model or self.DEFAULT_MODELS["chat"]
        self.video_model = video_model or self.DEFAULT_MODELS["video"]
        self.vision_model = vision_model or self.DEFAULT_MODELS["vision"]
        self.audio_model = audio_model or self.DEFAULT_MODELS["audio"]

        self._timeout = 180
        self._min_interval = 0.5
        self._last_request = 0.0

        # audio 端点缓存（首次探测成功后记住）
        self._audio_endpoint: Optional[str] = None

    # ==================== 路由 / 请求 ====================

    def _current_route(self) -> str:
        if self._route_index < len(self._routes):
            r = self._routes[self._route_index]
            if r not in self._failed_routes:
                return r
        for i, r in enumerate(self._routes):
            if r not in self._failed_routes:
                self._route_index = i
                return r
        self._failed_routes.clear()
        self._route_index = 0
        return self._routes[0]

    def _post(
        self,
        endpoint: str,
        data: dict,
        timeout: int = 180,
        raw: bool = False,
    ):
        """发送 POST 请求（带多路由切换）。

        raw=False（默认）：返回解析后的 JSON（dict）
        raw=True：返回原始 requests.Response（用于二进制响应）
        """
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        max_attempts = len(self._routes) * 4   # 503 时给更多重试机会
        last_err: Exception | None = None

        for _ in range(max_attempts):
            route = self._current_route()
            url = f"{route.rstrip('/')}/{endpoint.lstrip('/')}"
            try:
                resp = requests.post(url, headers=headers, json=data, timeout=timeout)
                self._last_request = time.time()

                # 503 服务端临时故障（如视频队列满）：不切路由，等待后重试
                if resp.status_code == 503:
                    try:
                        body = resp.json()
                        code = body.get("code", "")
                    except Exception:
                        code = ""
                    wait = 20 if code == "video_queue_full" else 5
                    logger.warning(
                        f"[agnes] {route} 503 ({code or 'busy'})，{wait}s 后重试同路由"
                    )
                    time.sleep(wait)
                    continue

                # 429 限流：等待后重试同路由
                if resp.status_code == 429:
                    time.sleep(3)
                    continue

                # 401/403 认证失败：当前路由不接受此 key，切下一个
                if resp.status_code in (401, 403):
                    logger.warning(f"[agnes] {route} 认证失败 {resp.status_code}，切换路由")
                    self._failed_routes.add(route)
                    continue

                if resp.status_code != 200:
                    try:
                        err = resp.json()
                        msg = err.get("error", {}).get("message", str(err))
                    except Exception:
                        msg = resp.text[:200]
                    raise RuntimeError(f"Agnes HTTP {resp.status_code}: {msg}")

                if raw:
                    return resp
                return resp.json()

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                self._failed_routes.add(route)
                last_err = e
                continue
            except requests.exceptions.RequestException as e:
                last_err = e
                time.sleep(2)
                continue

        raise RuntimeError(f"Agnes 所有路由失败: {last_err}")

    def _get(self, endpoint: str, params: dict | None = None, timeout: int = 30) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self._current_route().rstrip('/')}/{endpoint.lstrip('/')}"
        resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        if resp.status_code == 429:
            time.sleep(10)
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Agnes GET HTTP {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    # ==================== 工具 ====================

    @staticmethod
    def _to_size_tier(width: int, height: int) -> str:
        m = max(width, height)
        if m <= 1024:
            return "1K"
        if m <= 2048:
            return "2K"
        if m <= 3072:
            return "3K"
        return "4K"

    @staticmethod
    def _clamp_seed(seed: Optional[int]) -> int:
        if seed is None:
            return random.randint(0, 999)
        return max(-1, min(999, seed))

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
    def _img_to_b64(img: Image.Image) -> str:
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    @staticmethod
    def _parse_image_url(result: dict) -> str:
        url = None
        if result.get("data"):
            url = result["data"][0].get("url")
        if not url and result.get("output"):
            out = result["output"]
            if out.get("results"):
                url = out["results"][0].get("url")
            elif out.get("image_url"):
                url = out["image_url"]
        if not url:
            raise RuntimeError(f"Agnes 未返回图片: {json.dumps(result)[:200]}")
        return url

    @staticmethod
    def _download(url: str) -> Image.Image:
        if url.startswith("data:image"):
            b64 = re.sub(r"^data:image/.+;base64,", "", url)
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
        return await asyncio.to_thread(self._t2i_sync, prompt, width, height, seed)

    def _t2i_sync(self, prompt, width, height, seed) -> Image.Image:
        data = {
            "model": self.image_model,
            "prompt": prompt,
            "n": 1,
            "size": self._to_size_tier(width, height),
            "response_format": "url",
            "seed": self._clamp_seed(seed),
        }
        result = self._post("images/generations", data, timeout=self._timeout)
        return self._download(self._parse_image_url(result))

    # ==================== i2i（支持多图） ====================

    async def image_to_image(
        self,
        prompt: str,
        image: Union[Image.Image, List[Image.Image]],
        strength: float = 0.7,
        width: int = 1024,
        height: int = 1024,
        steps: int = 25,
        cfg: float = 7.5,
        seed: Optional[int] = None,
    ) -> Image.Image:
        return await asyncio.to_thread(
            self._i2i_sync, prompt, image, width, height, strength, seed,
        )

    def _i2i_sync(self, prompt, image, width, height, strength, seed) -> Image.Image:
        images = image if isinstance(image, list) else [image]
        images = [self._resize(img, 1024) for img in images]
        first = images[0]
        if width is None or height is None:
            width, height = first.size

        b64_list = [f"data:image/png;base64,{self._img_to_b64(img)}" for img in images]

        data = {
            "model": self.image_model,
            "prompt": prompt,
            "n": 1,
            "size": self._to_size_tier(width, height),
            "seed": self._clamp_seed(seed),
            "extra_body": {
                "image": b64_list,
                "response_format": "url",
            },
        }
        if strength and 0 < strength < 1:
            data["strength"] = strength

        result = self._post("images/generations", data, timeout=self._timeout)
        return self._download(self._parse_image_url(result))

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
            "model": self.text_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        result = self._post("chat/completions", data, timeout=120)
        if result.get("choices"):
            return result["choices"][0].get("message", {}).get("content", "")
        raise RuntimeError(f"Agnes chat 解析失败: {json.dumps(result)[:200]}")

    # ==================== vision ====================

    async def image_to_text(
        self,
        image: Image.Image,
        prompt: str = "请描述这张图片的内容",
        **kwargs,
    ) -> str:
        return await asyncio.to_thread(self._vision_sync, image, prompt)

    def _vision_sync(self, image, prompt) -> str:
        img = self._resize(image, 1024)
        b64 = self._img_to_b64(img)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            }
        ]
        data = {
            "model": self.vision_model,
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.7,
        }
        result = self._post("chat/completions", data, timeout=120)
        if result.get("choices"):
            return result["choices"][0].get("message", {}).get("content", "")
        raise RuntimeError(f"Agnes vision 解析失败: {json.dumps(result)[:200]}")

    # ==================== video ====================

    async def video_generation(self, prompt: str, **kwargs) -> dict:
        return await asyncio.to_thread(self._video_sync, prompt, **kwargs)

    def _video_sync(
        self,
        prompt: str,
        image: Optional[Image.Image] = None,
        duration: int = 10,
        width: int = 768,
        height: int = 768,
        callback_url: Optional[str] = None,
    ) -> dict:
        if duration < 4:
            duration = 5
        elif duration > 12:
            duration = 12

        if image:
            mode = "reference"
            images_data = [f"data:image/png;base64,{self._img_to_b64(image)}"]
        else:
            mode = "text"
            images_data = None

        if width == height:
            ar = "1:1"
        elif width > height:
            ar = "16:9"
        else:
            ar = "9:16"

        data = {
            "model": self.video_model,
            "prompt": prompt,
            "seconds": str(duration),
            "mode": mode,
            "size": "720P",
            "aspect_ratio": ar,
        }
        if images_data:
            data["images"] = images_data
        if callback_url:
            data["callback_url"] = callback_url

        return self._post("videos", data, timeout=300)

    async def video_status(self, video_id: str) -> dict:
        return await asyncio.to_thread(self._video_status_sync, video_id)

    def _video_status_sync(self, video_id: str) -> dict:
        return self._get(
            "agnesapi",
            params={"video_id": video_id, "model_name": self.video_model},
        )

    # ==================== audio / music ====================

    async def generate_audio(
        self,
        text: str,
        voice: str = "alloy",
        output_format: str = "mp3",
        duration: int = 30,
        **kwargs,
    ) -> bytes:
        """音频生成（TTS / 音乐）。

        首次调用会逐个尝试 AUDIO_ENDPOINTS 里的端点，
        成功后缓存到 self._audio_endpoint，后续直接复用。
        """
        return await asyncio.to_thread(
            self._audio_sync, text, voice, output_format, duration,
        )

    def _audio_sync(self, text, voice, output_format, duration) -> bytes:
        # 已缓存端点，直接走
        if self._audio_endpoint:
            try:
                return self._audio_call(
                    self._audio_endpoint, text, voice, output_format, duration,
                )
            except Exception:
                # 缓存失效，清掉重新探测
                self._audio_endpoint = None

        # 逐个探测
        last_err: Exception | None = None
        for endpoint in self.AUDIO_ENDPOINTS:
            try:
                result = self._audio_call(
                    endpoint, text, voice, output_format, duration,
                )
                self._audio_endpoint = endpoint
                return result
            except Exception as e:
                last_err = e
                continue

        raise RuntimeError(f"Agnes audio 所有端点均失败: {last_err}")

    def _audio_call(
        self, endpoint: str, text: str, voice: str,
        output_format: str, duration: int,
    ) -> bytes:
        """调用具体 audio 端点。自动兼容两种响应：
        - 二进制音频流（直接返回 bytes）
        - JSON（含 audio_url / url / b64 字段）
        """
        # 构造请求体：OpenAI TTS 用 input，音乐端点用 prompt
        if "speech" in endpoint:
            data = {
                "model": self.audio_model,
                "input": text,
                "voice": voice,
                "response_format": output_format,
            }
        else:
            data = {
                "model": self.audio_model,
                "prompt": text,
                "duration": duration,
                "response_format": output_format,
            }

        resp = self._post(endpoint, data, timeout=300, raw=True)
        ctype = resp.headers.get("Content-Type", "").lower()

        # 情况 A：二进制音频
        if ctype.startswith("audio/") or ctype == "application/octet-stream":
            if len(resp.content) > 500:
                return resp.content

        # 情况 B：JSON
        try:
            result = resp.json()
        except Exception:
            # 无法解析 JSON，但可能是音频数据被误判
            if len(resp.content) > 500:
                return resp.content
            raise RuntimeError(f"Agnes audio 返回无法解析: {resp.text[:200]}")

        # 尝试各种字段
        b64 = (
            result.get("audio_base64")
            or result.get("b64_json")
            or result.get("audio")
        )
        if b64 and isinstance(b64, str):
            if b64.startswith("data:"):
                b64 = b64.split(",", 1)[1]
            return base64.b64decode(b64)

        url = (
            result.get("audio_url")
            or result.get("url")
            or result.get("music_url")
        )
        if not url and result.get("data"):
            item = result["data"][0] if isinstance(result["data"], list) else result["data"]
            url = item.get("url") or item.get("audio_url")

        if url:
            r = requests.get(url, timeout=120)
            if r.status_code == 200:
                return r.content

        raise RuntimeError(f"Agnes audio 返回格式无法解析: {json.dumps(result)[:200]}")

    # ==================== 元信息 ====================

    def get_model(self) -> str:
        return self.image_model