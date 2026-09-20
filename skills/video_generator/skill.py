# skills/video_generator/skill.py
"""视频生成 skill。

能力：
    generate   文生视频（自动判断是否需要分段拼接长视频）

改造点：
    - 直接用 dispatcher.generate_video（已经处理 agnes 异步轮询）
    - 输出目录 → data/assets/video/
    - ffmpeg 可选：装了合并长视频，没装返回分段列表
"""

import asyncio
import logging
import random
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_VIDEO_DURATION = 60
DEFAULT_SEGMENT_DURATION = 10    # Agnes 单段上限 12s
DEFAULT_VIDEO_WIDTH = 768
DEFAULT_VIDEO_HEIGHT = 768

# Agnes 创建任务接口限流，段间冷却
SEGMENT_COOLDOWN_MIN = 10
SEGMENT_COOLDOWN_MAX = 15


class VideoGenerator:
    """视频生成器。"""

    NAME = "video_generator"
    VERSION = "2.0.0"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.output_dir = Path(
            self.config.get("output_dir", "./data/assets/video")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.default_duration = int(
            self.config.get("video_duration", DEFAULT_VIDEO_DURATION)
        )
        self.default_segment_duration = int(
            self.config.get("segment_duration", DEFAULT_SEGMENT_DURATION)
        )
        self.default_width = int(self.config.get("video_width", DEFAULT_VIDEO_WIDTH))
        self.default_height = int(self.config.get("video_height", DEFAULT_VIDEO_HEIGHT))
        self.auto_merge = bool(self.config.get("auto_merge", True))

    # ==================== 主入口 ====================

    async def execute(self, **kwargs) -> dict:
        action = kwargs.pop("action", "generate")
        try:
            if action == "generate":
                return self._ok(await self._generate(**kwargs))
            return self._err(f"未知 action: {action}")
        except Exception as e:
            msg = str(e)
            if "video_queue_full" in msg or "队列" in msg:
                logger.warning("Agnes 视频队列已满，请稍后重试")
                return self._err("视频服务队列已满，请稍后（几分钟）重试")
            logger.exception("VideoGenerator 执行失败")
            return self._err(msg)

    async def _generate(
        self,
        prompt: str = "",
        duration: Optional[int] = None,
        segment_duration: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        auto_merge: Optional[bool] = None,
    ) -> dict:
        start = time.time()

        if not prompt.strip():
            raise ValueError("prompt 不能为空")

        duration = int(duration or self.default_duration)
        segment_duration = int(segment_duration or self.default_segment_duration)
        width = int(width or self.default_width)
        height = int(height or self.default_height)
        if auto_merge is None:
            auto_merge = self.auto_merge

        # Agnes 单段上限 12 秒
        segment_duration = max(4, min(segment_duration, 12))
        # 时长钳制
        duration = max(segment_duration, min(duration, 600))

        # 是否需要分段
        if auto_merge and duration > segment_duration:
            return await self._generate_long(
                prompt, duration, segment_duration, width, height, start,
            )
        else:
            return await self._generate_single(
                prompt, min(duration, segment_duration), width, height, start,
            )

    # ==================== 单段 ====================

    async def _generate_single(
        self, prompt: str, duration: int, width: int, height: int, start: float,
    ) -> dict:
        from engines import dispatcher

        logger.info(f"🎬 生成单段视频 ({duration}s)...")
        video_bytes, used = await dispatcher.generate_video(
            prompt=prompt, duration=duration, width=width, height=height,
        )
        logger.info(f"✅ 引擎={used}，{len(video_bytes) // 1024} KB")

        out_path = self._make_path(prompt, suffix="video")
        out_path.write_bytes(video_bytes)

        return {
            "video_path": str(out_path),
            "video_url": self._to_url(out_path),
            "duration": duration,
            "segments": 1,
            "size_bytes": len(video_bytes),
            "engine": used,
            "prompt": prompt,
            "elapsed": f"{time.time() - start:.1f}s",
        }

    # ==================== 长视频 ====================

    async def _generate_long(
        self, prompt: str, duration: int, segment_duration: int,
        width: int, height: int, start: float,
    ) -> dict:
        from engines import dispatcher

        count = duration // segment_duration
        if duration % segment_duration:
            count += 1

        logger.info(f"🎬 长视频：{duration}s → {count} 段 × {segment_duration}s")

        temp_dir = self.output_dir / f"temp_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        segments: list[Path] = []
        used_engine = ""

        try:
            for i in range(count):
                logger.info(f"📹 第 {i+1}/{count} 段...")
                # 后续段加"连贯"提示词
                seg_prompt = prompt if i == 0 else f"{prompt}, continuing, keep consistent style"

                try:
                    video_bytes, used = await dispatcher.generate_video(
                        prompt=seg_prompt,
                        duration=segment_duration,
                        width=width,
                        height=height,
                    )
                    used_engine = used
                    seg_path = temp_dir / f"segment_{i:03d}.mp4"
                    seg_path.write_bytes(video_bytes)
                    segments.append(seg_path)
                    logger.info(f"✅ 第 {i+1} 段完成")
                except Exception as e:
                    logger.warning(f"⚠️ 第 {i+1} 段失败: {e}")

                # 段间冷却（避免限流）
                if i < count - 1:
                    cooldown = random.randint(
                        SEGMENT_COOLDOWN_MIN, SEGMENT_COOLDOWN_MAX,
                    )
                    logger.info(f"😴 冷却 {cooldown}s...")
                    await asyncio.sleep(cooldown)

            if not segments:
                raise RuntimeError("所有分段均生成失败")

            # 只有 1 段：直接搬出去
            if len(segments) == 1:
                final = self._make_path(prompt, suffix="video")
                shutil.move(str(segments[0]), str(final))
                return {
                    "video_path": str(final),
                    "video_url": self._to_url(final),
                    "duration": segment_duration,
                    "segments": 1,
                    "size_bytes": final.stat().st_size,
                    "engine": used_engine,
                    "prompt": prompt,
                    "elapsed": f"{time.time() - start:.1f}s",
                }

            # 多段：尝试合并
            merged_path = await asyncio.to_thread(
                self._merge_videos, segments, temp_dir, prompt,
            )

            if merged_path:
                final = self._make_path(prompt, suffix="merged")
                shutil.move(str(merged_path), str(final))
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {
                    "video_path": str(final),
                    "video_url": self._to_url(final),
                    "duration": duration,
                    "segments": len(segments),
                    "segment_duration": segment_duration,
                    "size_bytes": final.stat().st_size,
                    "engine": used_engine,
                    "prompt": prompt,
                    "elapsed": f"{time.time() - start:.1f}s",
                }

            # 合并失败：返回分段列表
            moved = []
            for p in segments:
                dest = self.output_dir / p.name
                shutil.move(str(p), str(dest))
                moved.append(str(dest))
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "video_paths": moved,
                "video_urls": [self._to_url(p) for p in moved],
                "duration": duration,
                "segments": len(segments),
                "segment_duration": segment_duration,
                "engine": used_engine,
                "prompt": prompt,
                "warning": "ffmpeg 未安装或合并失败，返回分段文件",
                "elapsed": f"{time.time() - start:.1f}s",
            }

        except Exception:
            # 失败保留临时目录，方便续传
            logger.warning(f"⚠️ 任务失败，临时文件保留在: {temp_dir}")
            raise

    # ==================== 工具 ====================

    def _make_path(self, prompt: str, suffix: str = "video") -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = "".join(
            c for c in prompt[:20] if c.isalnum() or c in " _-"
        ).strip().replace(" ", "_") or "video"
        return self.output_dir / f"{ts}_{suffix}_{safe}.mp4"

    @staticmethod
    def _has_ffmpeg() -> bool:
        return shutil.which("ffmpeg") is not None

    def _merge_videos(
        self, segments: list[Path], temp_dir: Path, prompt: str,
    ) -> Optional[Path]:
        """用 ffmpeg concat 合并分段。"""
        import subprocess

        if not self._has_ffmpeg():
            logger.warning("未找到 ffmpeg，跳过合并")
            return None

        try:
            list_file = temp_dir / "file_list.txt"
            with open(list_file, "w", encoding="utf-8") as f:
                for p in segments:
                    f.write(f"file '{p.resolve().as_posix()}'\n")

            output = temp_dir / "merged.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(output),
            ]
            r = subprocess.run(cmd, capture_output=True, timeout=180)
            if r.returncode == 0 and output.exists():
                logger.info(f"✅ 合并完成: {output.name}")
                return output
            logger.warning(f"ffmpeg 合并失败: {r.stderr.decode(errors='ignore')[:200]}")
            return None
        except Exception as e:
            logger.warning(f"合并异常: {e}")
            return None

    def _to_url(self, local_path) -> str:
        p = Path(local_path).resolve()
        root = Path("./data/assets").resolve()
        try:
            return f"/files/{p.relative_to(root).as_posix()}"
        except ValueError:
            return str(local_path)

    def _ok(self, result: dict) -> dict:
        return {
            "status": "success",
            "result": result,
            "skill": self.NAME,
            "version": self.VERSION,
            "executed_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _err(self, msg: str) -> dict:
        return {
            "status": "error",
            "error": msg,
            "skill": self.NAME,
            "version": self.VERSION,
            "executed_at": datetime.now().isoformat(timespec="seconds"),
        }