# server/api/v1/jobs.py
"""任务：创建 / 查询 / 列表。"""

import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.application.use_cases.generate_image import run_image_job
from server.infrastructure.jobs import Job, job_store

router = APIRouter()


class ImageJobRequest(BaseModel):
    prompt: str = ""
    preset: str | None = None
    width: int = Field(default=1024, ge=64, le=4096)
    height: int = Field(default=1024, ge=64, le=4096)
    engine: str | None = None


@router.post("/image", status_code=202)
async def create_image_job(req: ImageJobRequest):
    if not req.prompt and not req.preset:
        raise HTTPException(400, "prompt 和 preset 不能同时为空")

    job_id = uuid4().hex
    job = Job(id=job_id, type="image")
    await job_store.create(job)

    # 后台异步跑
    asyncio.create_task(run_image_job(job_id, req.model_dump()))

    return {"job_id": job_id, "status": "queued"}


@router.get("")
async def list_jobs(limit: int = 50):
    jobs = await job_store.list(limit)
    return [j.to_dict() for j in jobs]


@router.get("/{job_id}")
async def get_job(job_id: str):
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    return job.to_dict()