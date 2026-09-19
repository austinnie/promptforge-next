# server/api/v1/engines.py
"""引擎列表。"""

from fastapi import APIRouter

from engines import factory, list_engines

router = APIRouter()


@router.get("")
async def get_engines():
    raw = list_engines()
    return {
        name: {
            **info,
            "configured": factory.is_configured(name),
        }
        for name, info in raw.items()
    }