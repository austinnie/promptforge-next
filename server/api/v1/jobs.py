# server/api/v1/jobs.py
"""任务：创建 / 查询 / 列表。"""

import asyncio
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.application.use_cases.chat import run_chat
from server.application.use_cases.generate_audio import run_audio_job
from server.application.use_cases.generate_image import run_image_job
from server.application.use_cases.generate_video import run_video_job
from server.infrastructure.jobs import Job, job_store
from server.application.use_cases.generate_image_to_image import run_image_to_image_job

router = APIRouter()


# ==================== 请求模型 ====================

class ImageJobRequest(BaseModel):
    prompt: str = ""
    preset: str | None = None
    width: int = Field(default=1024, ge=64, le=4096)
    height: int = Field(default=1024, ge=64, le=4096)
    engine: str | None = None


class VideoJobRequest(BaseModel):
    prompt: str
    duration: int = Field(default=5, ge=4, le=12)
    width: int = Field(default=768, ge=64, le=2048)
    height: int = Field(default=768, ge=64, le=2048)
    engine: str | None = None


class AudioJobRequest(BaseModel):
    text: str
    voice: str = "alloy"
    format: str = "mp3"
    duration: int = Field(default=30, ge=1, le=300)
    engine: str | None = None


class ChatRequest(BaseModel):
    messages: list
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=8192)
    engine: str | None = None


# ==================== 创建任务 ====================

@router.post("/image", status_code=202)
async def create_image_job(req: ImageJobRequest):
    if not req.prompt and not req.preset:
        raise HTTPException(400, "prompt 和 preset 不能同时为空")
    job_id = uuid4().hex
    job = Job(id=job_id, type="image")
    await job_store.create(job)
    asyncio.create_task(run_image_job(job_id, req.model_dump()))
    return job.to_dict()

class ImageToImageJobRequest(BaseModel):
    prompt: str
    image_base64: str = Field(..., min_length=100,
                              description="参考图的 base64（可带 data:image 前缀）")
    strength: float = Field(default=0.7, ge=0.0, le=1.0)
    width: int = Field(default=1024, ge=64, le=4096)
    height: int = Field(default=1024, ge=64, le=4096)
    engine: str | None = None

@router.post("/image-to-image", status_code=202)
async def create_i2i_job(req: ImageToImageJobRequest):
    if not req.prompt.strip():
        raise HTTPException(400, "prompt 不能为空")
    if not req.image_base64 or len(req.image_base64) < 100:
        raise HTTPException(400, "image_base64 不能为空或过短")

    job_id = uuid4().hex
    job = Job(id=job_id, type="image_to_image")
    await job_store.create(job)
    asyncio.create_task(run_image_to_image_job(job_id, req.model_dump()))
    return job.to_dict()
    
@router.post("/video", status_code=202)
async def create_video_job(req: VideoJobRequest):
    if not req.prompt.strip():
        raise HTTPException(400, "prompt 不能为空")
    job_id = uuid4().hex
    job = Job(id=job_id, type="video")
    await job_store.create(job)
    asyncio.create_task(run_video_job(job_id, req.model_dump()))
    return job.to_dict()


@router.post("/audio", status_code=202)
async def create_audio_job(req: AudioJobRequest):
    if not req.text.strip():
        raise HTTPException(400, "text 不能为空")
    job_id = uuid4().hex
    job = Job(id=job_id, type="audio")
    await job_store.create(job)
    asyncio.create_task(run_audio_job(job_id, req.model_dump()))
    return job.to_dict()


# ==================== 同步接口 ====================

@router.post("/chat")
async def chat_sync(req: ChatRequest):
    """对话（同步返回，不走 job）。"""
    if not req.messages:
        raise HTTPException(400, "messages 不能为空")
    try:
        return await run_chat(
            messages=req.messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            engine=req.engine,
        )
    except Exception as e:
        raise HTTPException(500, f"chat 失败: {e}")


# ==================== 查询 ====================

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