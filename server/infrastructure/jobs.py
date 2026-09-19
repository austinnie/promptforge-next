# server/infrastructure/jobs.py
"""任务存储（内存版，重启即清空）。"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Job:
    id: str
    type: str
    status: str = "queued"          # queued / running / succeeded / failed
    progress: int = 0
    message: str = ""
    result: Dict = field(default_factory=dict)
    error: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobStore:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def create(self, job: Job) -> Job:
        async with self._lock:
            self._jobs[job.id] = job
        return job

    async def get(self, job_id: str) -> Optional[Job]:
        async with self._lock:
            return self._jobs.get(job_id)

    async def update(self, job_id: str, **kwargs) -> Optional[Job]:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            for k, v in kwargs.items():
                if hasattr(job, k):
                    setattr(job, k, v)
            job.updated_at = _now()
            return job

    async def list(self, limit: int = 50) -> List[Job]:
        async with self._lock:
            jobs = sorted(
                self._jobs.values(),
                key=lambda j: j.created_at,
                reverse=True,
            )
            return jobs[:limit]


job_store = JobStore()