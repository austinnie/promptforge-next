# server/application/use_cases/generate_image_to_image.py
"""图生图任务：解码参考图 → dispatcher.image_to_image → 落盘。"""

import base64
import io
import traceback

from PIL import Image

from engines import dispatcher
from server.core.config import settings
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


def _decode_image(image_base64: str) -> Image.Image:
    """从 base64 解码参考图。兼容 data:image/xxx;base64, 前缀。"""
    s = (image_base64 or "").strip()
    if not s:
        raise ValueError("参考图数据为空")
    if s.startswith("data:image"):
        s = s.split(",", 1)[1]
    try:
        raw = base64.b64decode(s)
    except Exception as e:
        raise ValueError(f"base64 解码失败: {e}")
    try:
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as e:
        raise ValueError(f"图片解析失败: {e}")


async def run_image_to_image_job(job_id: str, cmd: dict) -> None:
    """后台任务入口。异常时写入 failed 状态。"""
    try:
        prompt = (cmd.get("prompt") or "").strip()
        image_b64 = cmd.get("image_base64") or ""
        strength = float(cmd.get("strength") or 0.7)
        width = int(cmd.get("width") or 1024)
        height = int(cmd.get("height") or 1024)
        engine_prefer = cmd.get("engine") or None

        if not prompt:
            raise ValueError("prompt 不能为空")
        if not image_b64:
            raise ValueError("image_base64 不能为空")

        await _pub(job_id, 5, "准备中")

        # 解码参考图
        try:
            ref_image = _decode_image(image_b64)
        except ValueError as e:
            raise ValueError(f"参考图解析失败: {e}")

        await _pub(
            job_id, 15,
            f"参考图 {ref_image.size[0]}x{ref_image.size[1]}",
        )

        # 调 dispatcher（内部带降级）
        await _pub(job_id, 25, "调用引擎生成")
        img, used_engine = await dispatcher.image_to_image(
            prompt=prompt,
            image=ref_image,
            strength=strength,
            width=width,
            height=height,
            prefer=engine_prefer,
        )

        # 落盘
        await _pub(job_id, 85, "保存文件")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        key = f"{job_id}.png"
        storage = get_storage()
        await storage.save(key, buf.getvalue())
        url = await storage.url_for(key)

        result = {
            "key": key,
            "url": url,
            "width": img.size[0],
            "height": img.size[1],
            "engine": used_engine,
            "prompt": prompt,
            "strength": strength,
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