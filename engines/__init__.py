# engines/__init__.py
"""PromptForge-Next 引擎层。"""

import os
from pathlib import Path

# 尝试加载 .env（项目根目录）
try:
    from dotenv import load_dotenv
    _env = Path(__file__).resolve().parents[1] / ".env"
    if _env.exists():
        load_dotenv(_env)
except ImportError:
    pass

# 触发所有引擎的注册
from . import mock          # noqa: F401
from . import pollinations  # noqa: F401
from . import agnes         # noqa: F401
from . import freeapi       # noqa: F401   ← 新增
from . import siliconflow   # noqa: F401
from . import openrouter    # noqa: F401

from .base import BaseEngine  # noqa: F401
from .registry import get_engine_class, list_engines, register  # noqa: F401
from . import factory  # noqa: F401
from . import dispatcher  # noqa: F401

__all__ = [
    "BaseEngine",
    "register",
    "get_engine_class",
    "list_engines",
    "factory",
    "dispatcher",
]

__version__ = "0.1.0"