# server/api/v1/ws.py
"""WebSocket 任务进度。"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.core.events import event_bus
from server.infrastructure.jobs import job_store

router = APIRouter()


@router.websocket("/jobs/{job_id}/events")
async def job_events(websocket: WebSocket, job_id: str):
    await websocket.accept()

    job = await job_store.get(job_id)
    if not job:
        await websocket.send_json({"error": "任务不存在"})
        await websocket.close()
        return

    # 先推一次当前状态
    await websocket.send_json(job.to_dict())

    # 已经结束的直接关
    if job.status in ("succeeded", "failed"):
        await websocket.close()
        return

    q = await event_bus.subscribe(job_id)
    try:
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue
            await websocket.send_json(event)
            if event.get("status") in ("succeeded", "failed"):
                break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        await event_bus.unsubscribe(job_id, q)
        try:
            await websocket.close()
        except Exception:
            pass