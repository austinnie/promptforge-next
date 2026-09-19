# engines/dispatcher.py
"""多引擎调度：按能力路由 + 自动降级。"""

import logging
from typing import Optional

from PIL import Image

from . import factory

logger = logging.getLogger(__name__)

# 按能力声明的降级顺序
FALLBACK_CHAIN: dict[str, list[str]] = {
    "t2i": ["agnes", "pollinations", "siliconflow", "openrouter", "mock"],
    "i2i": ["agnes", "siliconflow"],
    "video": ["agnes"],
    "chat": ["agnes", "openrouter"],
    "vision": ["agnes"],
}


def _build_chain(capability: str, prefer: Optional[str] = None) -> list[str]:
    chain = FALLBACK_CHAIN.get(capability, [])
    if not chain:
        return []

    # 用户指定优先的引擎放最前
    if prefer and prefer in chain:
        chain = [prefer] + [n for n in chain if n != prefer]

    # 过滤掉未配置的引擎（mock 除外，它永远可用）
    available = [n for n in chain if n == "mock" or factory.is_configured(n)]
    return available or ["mock"]


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
    """带降级的文生图。

    返回 (image, engine_name)。
    """
    chain = _build_chain("t2i", prefer)
    if not chain:
        raise RuntimeError("没有可用的 t2i 引擎")

    last_err: Exception | None = None
    for name in chain:
        try:
            logger.info(f"[dispatcher] 尝试引擎: {name}")
            engine = factory.create(name)
            img = await engine.generate_single(
                prompt=prompt,
                negative=negative,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                seed=seed,
            )
            return img, name
        except Exception as e:
            logger.warning(f"[dispatcher] 引擎 {name} 失败: {e}")
            last_err = e
            continue

    raise RuntimeError(f"所有引擎均失败。最后错误: {last_err}")


async def image_to_image(
    prompt: str,
    image: Image.Image,
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
            logger.info(f"[dispatcher] 尝试引擎: {name}")
            engine = factory.create(name)
            img = await engine.image_to_image(
                prompt=prompt,
                image=image,
                strength=strength,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                seed=seed,
            )
            return img, name
        except Exception as e:
            logger.warning(f"[dispatcher] 引擎 {name} 失败: {e}")
            last_err = e
            continue

    raise RuntimeError(f"所有引擎均失败。最后错误: {last_err}")


def describe_chain() -> dict:
    """给诊断用：展示每条能力当前可用的引擎链。"""
    return {
        cap: _build_chain(cap)
        for cap in FALLBACK_CHAIN
    }