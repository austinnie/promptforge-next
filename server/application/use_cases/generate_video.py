# server/application/use_cases/generate_video.py
"""视频生成任务。"""

import traceback

from engines import dispatcher
from server.core.events import event_bus
from server.core.config import settings
from server.infrastructure.jobs import job_store
from server.infrastructure.storage import get_storage


async def _pub(job_id: str, progress: int, message: str, **extra):
    await job_store.update(job_id, progress=progress, message=message, **extra)
    await event_bus.publish(job_id, {
        "status": "running",
        "progress": progress,
        "message": message,
    })


async def run_video_job(job_id: str, cmd: dict) -> None:
    try:
        prompt = (cmd.get("prompt") or "").strip()
        duration = int(cmd.get("duration") or 5)
        width = int(cmd.get("width") or 768)
        height = int(cmd.get("height") or 768)
        engine_prefer = cmd.get("engine") or None

        if not prompt:
            raise ValueError("prompt 不能为空")

        # 时长钳制（Agnes 支持 4-12 秒）
        duration = max(4, min(duration, 12))

        await _pub(job_id, 5, f"准备生成 {duration}s 视频")

        await _pub(job_id, 15, "提交引擎")
        video_bytes, used_engine = await dispatcher.generate_video(
            prompt=prompt,
            duration=duration,
            width=width,
            height=height,
            prefer=engine_prefer,
            max_wait=900,
        )

        await _pub(job_id, 90, "保存文件")
        key = f"{job_id}.mp4"
        storage = get_storage()
        await storage.save(key, video_bytes)
        url = await storage.url_for(key)

        result = {
            "key": key,
            "url": url,
            "duration": duration,
            "size_bytes": len(video_bytes),
            "engine": used_engine,
            "prompt": prompt,
        }

        await job_store.update(
            job_id,
            status="succeeded",
            progress=100,
            message="完成",
            result=result,
        )
        await event_bus.publish(job_id, {
            "status": "succeeded",
            "progress": 100,
            "message": "完成",
            "result": result,
        })

    except Exception as e:
        traceback.print_exc()
        err = str(e)
        await job_store.update(
            job_id, status="failed", message=err, error=err,
        )
        await event_bus.publish(job_id, {
            "status": "failed", "message": err, "error": err,
        })