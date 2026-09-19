# server/application/use_cases/generate_audio.py
"""音频生成任务（TTS / 音乐）。"""

import traceback

from engines import dispatcher
from server.core.events import event_bus
from server.infrastructure.jobs import job_store
from server.infrastructure.storage import get_storage


async def _pub(job_id: str, progress: int, message: str, **extra):
    await job_store.update(job_id, progress=progress, message=message, **extra)
    await event_bus.publish(job_id, {
        "status": "running",
        "progress": progress,
        "message": message,
    })


async def run_audio_job(job_id: str, cmd: dict) -> None:
    try:
        text = (cmd.get("text") or "").strip()
        voice = cmd.get("voice") or "alloy"
        output_format = cmd.get("format") or "mp3"
        duration = int(cmd.get("duration") or 30)
        engine_prefer = cmd.get("engine") or None

        if not text:
            raise ValueError("text 不能为空")

        await _pub(job_id, 10, "调用音频引擎")
        audio_bytes, used_engine = await dispatcher.generate_audio(
            text=text,
            voice=voice,
            output_format=output_format,
            duration=duration,
            prefer=engine_prefer,
        )

        await _pub(job_id, 80, "保存文件")
        ext = output_format if output_format in ("mp3", "wav", "opus", "flac") else "mp3"
        key = f"{job_id}.{ext}"
        storage = get_storage()
        await storage.save(key, audio_bytes)
        url = await storage.url_for(key)

        result = {
            "key": key,
            "url": url,
            "format": ext,
            "size_bytes": len(audio_bytes),
            "engine": used_engine,
            "text": text[:200],
            "voice": voice,
        }

        await job_store.update(
            job_id, status="succeeded", progress=100,
            message="完成", result=result,
        )
        await event_bus.publish(job_id, {
            "status": "succeeded", "progress": 100,
            "message": "完成", "result": result,
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