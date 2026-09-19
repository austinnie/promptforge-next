# server/api/v1/files.py
"""静态文件访问（本地存储时用）。"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from server.core.config import settings

router = APIRouter()


@router.get("/{key:path}")
async def get_file(key: str):
    root = settings.storage_local_dir.resolve()
    p = (root / key).resolve()
    if not str(p).startswith(str(root)):
        raise HTTPException(400, "非法路径")
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "文件不存在")
    return FileResponse(p)