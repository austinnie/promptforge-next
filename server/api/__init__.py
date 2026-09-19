# server/api/__init__.py
"""API 路由汇总。"""

from fastapi import APIRouter

from server.api.v1 import engines, files, jobs, presets, system, ws


def build_api_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(system.router, prefix="/system", tags=["system"])
    router.include_router(engines.router, prefix="/engines", tags=["engines"])
    router.include_router(presets.router, prefix="/presets", tags=["presets"])
    router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
    router.include_router(ws.router, tags=["ws"])
    return router


def build_files_router() -> APIRouter:
    router = APIRouter()
    router.include_router(files.router, prefix="/files", tags=["files"])
    return router