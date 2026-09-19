# server/api/v1/system.py
"""系统信息：给 App 显示本机 IP。"""

import socket

from fastapi import APIRouter

from server.core.config import settings

router = APIRouter()


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


@router.get("/info")
async def system_info():
    return {
        "version": "0.1.0",
        "deployment": settings.deployment,
        "host": settings.host,
        "port": settings.port,
        "local_ip": get_local_ip(),
        "storage_backend": settings.storage_backend,
        "safe_mode": settings.safe_mode,
    }