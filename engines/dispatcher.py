# engines/dispatcher.py
"""多引擎调度：按能力路由 + 自动降级。

能力矩阵：
    t2i      文生图   → Image.Image
    i2i      图生图   → Image.Image
    chat     对话     → str
    vision   图片反推 → str
    audio    语音合成 → bytes
    video    视频生成 → bytes
"""

import asyncio
import logging
from typing import Optional, Union

import requests
from PIL import Image

from . import factory

logger = logging.getLogger(__name__)

# 按能力声明的降级顺序
# chat / vision / audio 都把 agnes 放前面（pollinations key 权限受限）
FALLBACK_CHAIN: dict[str, list[str]] = {
    "t2i": ["agnes", "pollinations", "freeapi", "siliconflow", "openrouter", "mock"],
    "i2i": ["agnes", "pollinations"],
    "chat": ["agnes", "pollinations"],
    "vision": ["agnes", "pollinations"],
    "audio": ["agnes", "pollinations"],
    "video": ["agnes", "pollinations"],
}


# ==================== 内部工具 ====================


def _build_chain(capability: str, prefer: Optional[str] = None) -> list[str]:
    chain = FALLBACK_CHAIN.get(capability, [])
    if not chain:
        return []

    if prefer and prefer in chain:
        chain = [prefer] + [n for n in chain if n != prefer]

    available = [n for n in chain if n == "mock" or factory.is_configured(n)]
    return available or ["mock"]


def _download_bytes(url: str, timeout: int = 120) -> bytes:
    resp = requests.get(url, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(f"下载失败 ({resp.status_code}): {url[:120]}")
    return resp.content


async def _poll_agnes_video(
    engine,
    video_id: str,
    poll_interval: int = 10,
    max_wait: int = 900,
) -> str:
    """轮询 Agnes 视频，返回 video_url。"""
    import time

    start = time.time()
    consecutive_fail = 0
    backoff = 15

    while time.time() - start < max_wait:
        try:
            status = await engine.video_status(video_id)
            consecutive_fail = 0
            backoff = 15
        except Exception as e:
            consecutive_fail += 1
            logger.warning(f"[video] 状态查询失败 ({consecutive_fail}): {str(e)[:120]}")
            if consecutive_fail >= 5:
                raise RuntimeError(f"状态查询连续失败 {consecutive_fail} 次")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        state = status.get("status", "")
        progress = status.get("progress", 0)
        logger.info(f"[video] agnes 状态: {state}, 进度: {progress}%")

        if state in ("completed", "succeeded"):
            url = status.get("video_url") or status.get("url")
            if url:
                return url
            await asyncio.sleep(poll_interval)
            continue

        if state in ("failed", "error"):
            raise RuntimeError(f"视频生成失败: {status.get('error', '未知错误')}")

        sleep_time = 8 if (progress and progress >= 90) else poll_interval
        await asyncio.sleep(sleep_time)

    raise RuntimeError(f"视频生成超时 ({max_wait}s)")


# ==================== t2i ====================


async def generate_image(
    prompt: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    cfg: float = 7.5,
    seed: Optional[int] = None,
    prefer: Optional[str] = None,
) -> tuple[Image.Image, str]:
    chain = _build_chain("t2i", prefer)
    if not chain:
        raise RuntimeError("没有可用的 t2i 引擎")

    last_err: Exception | None = None
    for name in chain:
        try:
            logger.info(f"[t2i] 尝试: {name}")
            engine = factory.create(name)
            img = await engine.generate_single(
                prompt=prompt, negative=negative,
                width=width, height=height,
                steps=steps, cfg=cfg, seed=seed,
            )
            return img, name
        except Exception as e:
            logger.warning(f"[t2i] {name} 失败: {str(e)[:150]}")
            last_err = e
            continue

    raise RuntimeError(f"所有 t2i 引擎均失败。最后错误: {last_err}")


# ==================== i2i ====================


async def image_to_image(
    prompt: str,
    image: Union[Image.Image, list[Image.Image]],
    strength: float = 0.7,
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    cfg: float = 7.5,
    seed: Optional[int] = None,
    prefer: Optional[str] = None,
) -> tuple[Image.Image, str]:
    chain = _build_chain("i2i", prefer)
    if not chain:
        raise RuntimeError("没有可用的 i2i 引擎")

    last_err: Exception | None = None
    for name in chain:
        try:
            logger.info(f"[i2i] 尝试: {name}")
            engine = factory.create(name)
            img = await engine.image_to_image(
                prompt=prompt, image=image, strength=strength,
                width=width, height=height,
                steps=steps, cfg=cfg, seed=seed,
            )
            return img, name
        except Exception as e:
            logger.warning(f"[i2i] {name} 失败: {str(e)[:150]}")
            last_err = e
            continue

    raise RuntimeError(f"所有 i2i 引擎均失败。最后错误: {last_err}")


# ==================== chat ====================


async def chat(
    messages: list,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    prefer: Optional[str] = None,
) -> tuple[str, str]:
    chain = _build_chain("chat", prefer)
    if not chain:
        raise RuntimeError("没有可用的 chat 引擎")

    last_err: Exception | None = None
    for name in chain:
        try:
            logger.info(f"[chat] 尝试: {name}")
            engine = factory.create(name)
            text = await engine.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return text, name
        except Exception as e:
            logger.warning(f"[chat] {name} 失败: {str(e)[:150]}")
            last_err = e
            continue

    raise RuntimeError(f"所有 chat 引擎均失败。最后错误: {last_err}")


# ==================== vision ====================


async def image_to_text(
    image: Image.Image,
    prompt: str = "描述这张图片",
    prefer: Optional[str] = None,
) -> tuple[str, str]:
    chain = _build_chain("vision", prefer)
    if not chain:
        raise RuntimeError("没有可用的 vision 引擎")

    last_err: Exception | None = None
    for name in chain:
        try:
            logger.info(f"[vision] 尝试: {name}")
            engine = factory.create(name)
            text = await engine.image_to_text(image=image, prompt=prompt)
            return text, name
        except Exception as e:
            logger.warning(f"[vision] {name} 失败: {str(e)[:150]}")
            last_err = e
            continue

    raise RuntimeError(f"所有 vision 引擎均失败。最后错误: {last_err}")


# ==================== audio ====================


async def generate_audio(
    text: str,
    voice: str = "alloy",
    output_format: str = "mp3",
    duration: int = 30,
    prefer: Optional[str] = None,
) -> tuple[bytes, str]:
    chain = _build_chain("audio", prefer)
    if not chain:
        raise RuntimeError("没有可用的 audio 引擎")

    last_err: Exception | None = None
    for name in chain:
        try:
            logger.info(f"[audio] 尝试: {name}")
            engine = factory.create(name)
            audio = await engine.generate_audio(
                text=text, voice=voice,
                output_format=output_format, duration=duration,
            )
            return audio, name
        except Exception as e:
            logger.warning(f"[audio] {name} 失败: {str(e)[:150]}")
            last_err = e
            continue

    raise RuntimeError(f"所有 audio 引擎均失败。最后错误: {last_err}")


# ==================== video ====================


async def generate_video(
    prompt: str,
    image: Optional[Image.Image] = None,
    duration: int = 5,
    width: int = 768,
    height: int = 768,
    prefer: Optional[str] = None,
    poll_interval: int = 10,
    max_wait: int = 900,
) -> tuple[bytes, str]:
    chain = _build_chain("video", prefer)
    if not chain:
        raise RuntimeError("没有可用的 video 引擎")

    last_err: Exception | None = None
    for name in chain:
        try:
            logger.info(f"[video] 尝试: {name}")
            engine = factory.create(name)
            result = await engine.video_generation(
                prompt=prompt, image=image,
                duration=duration, width=width, height=height,
            )

            # 情况 A：同步返回（pollinations）
            if result.get("_sync") and "video_bytes" in result:
                return result["video_bytes"], name

            # 情况 B：异步任务（agnes）
            video_id = (
                result.get("video_id")
                or result.get("id")
                or result.get("task_id")
            )
            if not video_id:
                raise RuntimeError(f"{name} 未返回 video_id: {str(result)[:200]}")

            video_url = await _poll_agnes_video(
                engine, video_id,
                poll_interval=poll_interval,
                max_wait=max_wait,
            )
            video_bytes = await asyncio.to_thread(_download_bytes, video_url)
            return video_bytes, name

        except Exception as e:
            logger.warning(f"[video] {name} 失败: {str(e)[:150]}")
            last_err = e
            continue

    raise RuntimeError(f"所有 video 引擎均失败。最后错误: {last_err}")


# ==================== 诊断 ====================


def describe_chain() -> dict:
    return {cap: _build_chain(cap) for cap in FALLBACK_CHAIN}