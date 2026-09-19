# server/core/events.py
"""任务事件总线：用于 WebSocket 广播进度。"""

import asyncio
from typing import Dict, List


class EventBus:
    """一个 job_id → 多个订阅者 queue。"""

    def __init__(self):
        self._queues: Dict[str, List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, job_id: str) -> asyncio.Queue:
        async with self._lock:
            q: asyncio.Queue = asyncio.Queue(maxsize=100)
            self._queues.setdefault(job_id, []).append(q)
            return q

    async def unsubscribe(self, job_id: str, q: asyncio.Queue) -> None:
        async with self._lock:
            queues = self._queues.get(job_id)
            if not queues:
                return
            try:
                queues.remove(q)
            except ValueError:
                pass
            if not queues:
                self._queues.pop(job_id, None)

    async def publish(self, job_id: str, event: dict) -> None:
        async with self._lock:
            queues = list(self._queues.get(job_id, []))
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


event_bus = EventBus()