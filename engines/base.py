# engines/base.py
"""引擎基类。"""

from abc import ABC, abstractmethod
from typing import Optional, Set

from PIL import Image


class BaseEngine(ABC):
    """所有引擎的基类。

    子类必须声明：
        NAME: 引擎唯一标识
        CAPABILITIES: 能力集合（t2i / i2i / video / audio / chat / vision）
    """

    NAME: str = ""
    CAPABILITIES: Set[str] = set()

    # ========== 主接口 ==========

    @abstractmethod
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
        """文生图。所有 t2i 引擎必须实现。"""

    # ========== 可选接口 ==========

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
        raise NotImplementedError(f"{self.NAME} 不支持 image_to_image")

    async def video_generation(self, prompt: str, **kwargs) -> dict:
        raise NotImplementedError(f"{self.NAME} 不支持 video_generation")

    async def chat(self, messages: list, **kwargs) -> str:
        raise NotImplementedError(f"{self.NAME} 不支持 chat")

    async def image_to_text(self, image: Image.Image, prompt: str = "描述这张图", **kwargs) -> str:
        raise NotImplementedError(f"{self.NAME} 不支持 image_to_text")

    # ========== 元信息 ==========

    def get_name(self) -> str:
        return self.NAME or self.__class__.__name__

    def get_model(self) -> str:
        return getattr(self, "model", "")

    def supports(self, capability: str) -> bool:
        return capability in self.CAPABILITIES