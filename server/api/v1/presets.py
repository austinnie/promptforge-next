# server/api/v1/presets.py
"""预设列表 / 详情。"""

from fastapi import APIRouter, HTTPException

from packages.forge_core import get_default_bridge
from packages.forge_core.presets_meta import (
    CATEGORY_ORDER,
    get_category,
    get_display_name,
)

router = APIRouter()


@router.get("")
async def list_presets():
    bridge = get_default_bridge()
    if not bridge.is_ready():
        raise HTTPException(503, "预设系统未就绪")

    grouped: dict[str, list[dict]] = {}
    for name in bridge.list_presets():
        cat = get_category(name)
        grouped.setdefault(cat, []).append({
            "name": name,
            "display": get_display_name(name),
        })

    ordered: dict[str, list[dict]] = {}
    for cat in CATEGORY_ORDER:
        if cat in grouped:
            ordered[cat] = sorted(grouped[cat], key=lambda x: x["name"])
    for cat, items in grouped.items():
        if cat not in ordered:
            ordered[cat] = sorted(items, key=lambda x: x["name"])

    return ordered


@router.get("/{name}")
async def get_preset(name: str):
    bridge = get_default_bridge()
    data = bridge.load_preset(name)
    if not data:
        raise HTTPException(404, f"未找到预设: {name}")
    return data