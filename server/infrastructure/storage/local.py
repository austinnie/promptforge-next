# server/infrastructure/storage/local.py
"""本地文件存储。"""

import asyncio
from pathlib import Path

from .base import Storage


class LocalStorage(Storage):
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """防路径穿越。"""
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError(f"非法路径: {key}")
        return p

    async def save(self, key: str, data: bytes) -> str:
        p = self._resolve(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(p.write_bytes, data)
        return key

    async def url_for(self, key: str) -> str:
        # 相对路径，前端拼 base_url
        return f"/files/{key}"

    def path_for(self, key: str) -> str:
        return str(self._resolve(key))