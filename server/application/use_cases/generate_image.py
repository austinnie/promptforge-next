# server/application/use_cases/generate_image.py
"""文生图任务：预设 + 安全 + 引擎 + 落盘。"""

import io
import traceback

from engines import dispatcher
from packages.forge_core import SafetyChecker, get_default_bridge
from server.core.config import settings
from server.core.events import event_bus
from server.infrastructure.jobs import job_store
from server.infrastructure.storage import get_storage
from server.application.use_cases._naming import make_key

async def _pub(job_id: str, progress: int, message: str, **extra):
    await job_store.update(job_id, progress=progress, message=message, **extra)
    await event_bus.publish(job_id, {
        "status": "running",
        "progress": progress,
        "message": message,
    })


async def run_image_job(job_id: str, cmd: dict) -> None:
    """后台任务入口。异常时写入 failed 状态。"""
    try:
        # ---------- 1. 参数解析 ----------
        prompt = (cmd.get("prompt") or "").strip()
        preset = cmd.get("preset") or None
        width = int(cmd.get("width") or 1024)
        height = int(cmd.get("height") or 1024)
        engine_prefer = cmd.get("engine") or None

        if not prompt and not preset:
            raise ValueError("prompt 和 preset 不能同时为空")

        await _pub(job_id, 5, "准备中")

        # ---------- 2. 安全检测 ----------
        if settings.enable_safety_check and prompt:
            is_unsafe, matched = SafetyChecker.check(prompt)
            if is_unsafe:
                cleaned = SafetyChecker.sanitize(prompt)
                if not cleaned or SafetyChecker.get_score(prompt) > 30:
                    raise ValueError(f"检测到不安全内容: {matched[:3]}")
                prompt = cleaned
                await _pub(job_id, 10, "已自动过滤敏感词")

        # ---------- 3. 预设组合 ----------
        final_prompt = prompt
        if preset:
            bridge = get_default_bridge()
            if not bridge.is_ready():
                raise RuntimeError("预设系统未就绪")
            final_prompt, _ = bridge.build_prompt(
                preset=preset,
                mode="random",
                subject_override=prompt if prompt else None,
                max_tokens=77,
                return_detail=True,
            )
            await _pub(job_id, 20, f"预设 {preset} 已组合")

        if not final_prompt:
            final_prompt = "masterpiece, best quality"

        # ---------- 4. 引擎生成 ----------
        await _pub(job_id, 30, "调用引擎生成")
        img, used_engine = await dispatcher.generate_image(
            prompt=final_prompt,
            width=width,
            height=height,
            prefer=engine_prefer,
        )

        # ---------- 5. 落盘 ----------
        await _pub(job_id, 85, "保存文件")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        key = make_key(final_prompt, job_id, ext="png")
        storage = get_storage()
        await storage.save(key, buf.getvalue())
        url = await storage.url_for(key)

        result = {
            "key": key,
            "url": url,
            "width": img.size[0],
            "height": img.size[1],
            "engine": used_engine,
            "prompt": final_prompt,
            "preset": preset,
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
            job_id,
            status="failed",
            message=err,
            error=err,
        )
        await event_bus.publish(job_id, {
            "status": "failed",
            "message": err,
            "error": err,
        })