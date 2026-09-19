# engines/factory.py
"""根据环境变量创建引擎实例。"""

import os
from typing import Dict

from .base import BaseEngine
from .registry import get_engine_class

# 引擎名 → {__init__ 参数名: 环境变量名}
ENGINE_ENV_KEYS: Dict[str, Dict[str, str]] = {
    "agnes": {
        "api_key": "AGNES_API_KEY",
        "base_url": "AGNES_BASE_URL",
        "image_model": "AGNES_IMAGE_MODEL",
    },
    "pollinations": {
        "api_key": "POLLINATIONS_API_KEY",
        "model": "POLLINATIONS_MODEL",
    },
    "siliconflow": {
        "api_key": "SILICONFLOW_API_KEY",
        "model": "SILICONFLOW_MODEL",
    },
    "openrouter": {
        "api_key": "OPENROUTER_API_KEY",
        "model": "OPENROUTER_MODEL",
    },
    "mock": {},
}


def create(name: str, overrides: dict | None = None) -> BaseEngine:
    """创建引擎实例。

    - 从 os.environ 读取该引擎的配置
    - overrides 覆盖环境变量（用于测试或临时切换）
    """
    cls = get_engine_class(name)
    keymap = ENGINE_ENV_KEYS.get(name, {})
    kwargs: dict = {}
    for arg_name, env_name in keymap.items():
        val = os.getenv(env_name, "")
        if val:
            kwargs[arg_name] = val
    if overrides:
        kwargs.update(overrides)
    return cls(**kwargs)


def is_configured(name: str) -> bool:
    """粗略判断引擎是否已配置好（用于 dispatcher 跳过无 key 的引擎）。"""
    keymap = ENGINE_ENV_KEYS.get(name, {})
    # mock 永远可用
    if not keymap:
        return True
    for arg_name, env_name in keymap.items():
        # api_key 类必须非空
        if arg_name in ("api_key", "api_token") and not os.getenv(env_name):
            return False
    return True