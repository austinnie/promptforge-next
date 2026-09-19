# server/infrastructure/storage/__init__.py
"""存储工厂。"""

from functools import lru_cache

from server.core.config import settings

from .base import Storage
from .local import LocalStorage


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.storage_local_dir)
    raise ValueError(f"未支持的 storage_backend: {settings.storage_backend}")


__all__ = ["Storage", "LocalStorage", "get_storage"]