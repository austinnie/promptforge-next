# server/infrastructure/storage/base.py
"""存储抽象。"""

from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes) -> str:
        """保存文件，返回 key。"""

    @abstractmethod
    async def url_for(self, key: str) -> str:
        """返回可访问的 URL（相对或绝对）。"""

    @abstractmethod
    def path_for(self, key: str) -> str:
        """返回本地绝对路径（仅本地存储有意义）。"""