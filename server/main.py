# server/main.py
"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api import build_api_router, build_files_router
from server.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="PromptForge-Next API",
        version="0.1.0",
        description="Flutter + FastAPI，多引擎 API 编排",
    )

    # 开发期全开，生产收紧
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(build_api_router())
    app.include_router(build_files_router())

    @app.get("/")
    async def root():
        return {
            "name": "PromptForge-Next API",
            "version": "0.1.0",
            "docs": "/docs",
            "api": "/api/v1",
            "deployment": settings.deployment,
        }

    return app


app = create_app()