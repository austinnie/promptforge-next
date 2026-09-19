# engines/registry.py
"""引擎注册表。"""

from typing import Dict, Type

from .base import BaseEngine

_ENGINES: Dict[str, Type[BaseEngine]] = {}


def register(name: str):
    """装饰器：把引擎类注册到全局表。"""
    def deco(cls: Type[BaseEngine]):
        cls.NAME = name
        _ENGINES[name] = cls
        return cls
    return deco


def get_engine_class(name: str) -> Type[BaseEngine]:
    if name not in _ENGINES:
        raise ValueError(f"未注册的引擎: {name}（已注册: {sorted(_ENGINES)}）")
    return _ENGINES[name]


def list_engines() -> Dict[str, dict]:
    """给 API 用：列出所有引擎及能力。"""
    return {
        n: {
            "name": n,
            "class": c.__name__,
            "capabilities": sorted(c.CAPABILITIES),
        }
        for n, c in _ENGINES.items()
    }


def find_by_capability(capability: str) -> list[str]:
    return [n for n, c in _ENGINES.items() if capability in c.CAPABILITIES]