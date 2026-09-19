# skills/voice_assistant/skill.py
"""语音助手 skill。

能力：
    tts           文字转语音（edge-tts）
    list_voices   列出可用语音

不做的：
    stt           语音识别需要 whisper（本地模型），按项目原则不实现

特性：
    - 长文本自动分段（默认 5000 字/段）
    - Markdown 自动清理
    - 可选 ffmpeg 合并（装了合，没装返回分段列表）
"""

import asyncio
import logging
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from mutagen import File as MutagenFile
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

from .voices import DEFAULT_VOICES


class VoiceAssistant:
    """语音合成助手。"""

    NAME = "voice_assistant"
    VERSION = "1.0.0"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.output_dir = Path(
            self.config.get("output_dir", "./data/assets/voice")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.default_voice = self.config.get(
            "default_voice", "zh-CN-XiaoxiaoNeural"
        )
        self.default_speed = float(self.config.get("default_speed", 1.0))
        self.chunk_size = int(self.config.get("chunk_size", 5000))
        self.max_segments = int(self.config.get("max_segments", 50))

        if not EDGE_TTS_AVAILABLE:
            logger.warning("edge-tts 未安装，TTS 功能不可用")

    # ==================== 主入口 ====================

    async def execute(self, **kwargs) -> dict:
        action = kwargs.pop("action", "tts")     # ← 用 pop
        try:
            if action == "list_voices":
                return self._ok(self._list_voices())
            if action == "tts":
                return self._ok(await self._tts_action(**kwargs))
            return self._err(f"未知 action: {action}")
        except Exception as e:
            logger.exception("VoiceAssistant 执行失败")
            return self._err(str(e))

    # ==================== tts ====================

    async def _tts_action(
        self,
        text: str = "",
        text_file: str = "",
        voice: str = "",
        speed: Optional[float] = None,
        output_file: str = "",
        auto_split: bool = False,
    ) -> dict:
        if not EDGE_TTS_AVAILABLE:
            raise RuntimeError("edge-tts 未安装，请 pip install edge-tts")

        # 1. 文本来源
        if not text and text_file:
            text = await asyncio.to_thread(self._read_text_file, text_file)
        if not text:
            raise ValueError("必须提供 text 或 text_file")

        voice = voice or self.default_voice
        speed = speed if speed is not None else self.default_speed

        # 2. 分段
        chunks = self._split_text(text, self.chunk_size, auto_split)
        logger.info(f"文本 {len(text)} 字，分成 {len(chunks)} 段")

        # 3. 逐段生成
        audio_paths: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            seg_name = self._make_filename(chunk, voice, suffix=f"_{i:02d}")
            seg_path = self.output_dir / seg_name
            await self._tts_one(chunk, voice, speed, str(seg_path))
            audio_paths.append(str(seg_path))

        # 4. 单段直接返回
        if len(audio_paths) == 1:
            final_path = audio_paths[0]
            if output_file:
                final_path = await asyncio.to_thread(
                    self._move_file, final_path, output_file
                )
            return {
                "audio_path": final_path,
                "duration": self._get_duration(final_path),
                "text_preview": text[:100] + ("..." if len(text) > 100 else ""),
                "voice": voice,
                "speed": speed,
                "chunks": 1,
            }

        # 5. 多段合并（可选）
        merged = None
        if output_file:
            merge_target = output_file
        else:
            merge_target = str(
                self.output_dir
                / self._make_filename(chunks[0], voice, suffix="_merged")
            )

        if self._has_ffmpeg():
            merged = await asyncio.to_thread(
                self._merge_audio, audio_paths, merge_target
            )

        if merged:
            return {
                "audio_path": merged,
                "duration": self._get_duration(merged),
                "text_preview": text[:100] + ("..." if len(text) > 100 else ""),
                "voice": voice,
                "speed": speed,
                "chunks": len(chunks),
                "segment_files": audio_paths,
            }

        # 6. 没 ffmpeg，返回分段列表
        return {
            "audio_paths": audio_paths,
            "text_preview": text[:100] + ("..." if len(text) > 100 else ""),
            "voice": voice,
            "speed": speed,
            "chunks": len(chunks),
            "warning": "ffmpeg 未安装，返回分段文件",
        }

    async def _tts_one(self, text: str, voice: str, speed: float, out_path: str):
        """单段 TTS。"""
        rate_pct = int((speed - 1.0) * 100)
        rate = f"{rate_pct:+d}%"

        communicate = edge_tts.Communicate(text, voice, rate=rate)
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        await communicate.save(out_path)

    # ==================== list_voices ====================

    def _list_voices(self) -> dict:
        # 先用本地常量，避免每次都联网
        voices = [
            {"name": n, "locale": loc, "gender": g, "style": "General"}
            for n, loc, g in DEFAULT_VOICES
        ]
        return {
            "voices": voices,
            "count": len(voices),
            "default": self.default_voice,
        }

    async def list_online_voices(self) -> dict:
        """联网拉取 edge-tts 的完整语音列表（可选）。"""
        if not EDGE_TTS_AVAILABLE:
            raise RuntimeError("edge-tts 未安装")
        raw = await edge_tts.list_voices()
        voices = [
            {
                "name": v.get("ShortName", ""),
                "locale": v.get("Locale", ""),
                "gender": v.get("Gender", ""),
                "style": (v.get("StyleList") or ["General"])[0],
            }
            for v in raw
        ]
        return {"voices": voices, "count": len(voices)}

    # ==================== 文本处理 ====================

    def _read_text_file(self, file_path: str) -> str:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        text = p.read_text(encoding="utf-8", errors="replace")
        return self._clean_markdown(text).strip()

    @staticmethod
    def _clean_markdown(text: str) -> str:
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[-=*]{3,}\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"!\[(.+?)\]\(.+?\)", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"^[=\-]{10,}\s*$", "", text, flags=re.MULTILINE)
        return text

    def _split_text(
        self, text: str, chunk_size: int, auto_split: bool,
    ) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        # 按中英文句末标点切
        sentences = re.split(r"(?<=[。！？；.!?;])\s*", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: list[str] = []
        current = ""
        for s in sentences:
            if len(current) + len(s) <= chunk_size:
                current += s
            else:
                if current:
                    chunks.append(current)
                # 单句超长，硬切
                while len(s) > chunk_size:
                    chunks.append(s[:chunk_size])
                    s = s[chunk_size:]
                current = s
        if current:
            chunks.append(current)

        # 超限合并
        if len(chunks) > self.max_segments:
            logger.warning(
                f"分段 {len(chunks)} 超过上限 {self.max_segments}，合并相邻段"
            )
            merged: list[str] = []
            for i in range(0, len(chunks), 2):
                if i + 1 < len(chunks):
                    merged.append(chunks[i] + chunks[i + 1])
                else:
                    merged.append(chunks[i])
            chunks = merged

        return chunks

    # ==================== 文件工具 ====================

    def _make_filename(self, text: str, voice: str, suffix: str = "") -> str:
        preview = re.sub(r"[^\w\u4e00-\u9fff]", "", text[:15]) or "语音"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        voice_short = voice.split("-")[0] if "-" in voice else voice[:8]
        return f"{preview}_{voice_short}_{ts}{suffix}.mp3"

    @staticmethod
    def _move_file(src: str, dst: str) -> str:
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src, dst)
        return dst

    @staticmethod
    def _has_ffmpeg() -> bool:
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def _merge_audio(paths: list[str], output: str) -> Optional[str]:
        """用 ffmpeg concat 合并音频。"""
        try:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            list_file = Path(paths[0]).parent / f"_merge_{datetime.now().timestamp()}.txt"
            with open(list_file, "w", encoding="utf-8") as f:
                for p in paths:
                    abs_p = str(Path(p).resolve()).replace("'", "'\\''")
                    f.write(f"file '{abs_p}'\n")

            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(list_file), "-c", "copy", output,
            ]
            r = subprocess.run(cmd, capture_output=True, timeout=120)
            list_file.unlink(missing_ok=True)

            if r.returncode == 0 and Path(output).exists():
                return output
            logger.warning(f"ffmpeg 合并失败: {r.stderr.decode(errors='ignore')[:200]}")
            return None
        except Exception as e:
            logger.warning(f"合并异常: {e}")
            return None

    @staticmethod
    def _get_duration(path: str) -> float:
        if not MUTAGEN_AVAILABLE:
            return 0.0
        try:
            f = MutagenFile(path)
            return round(float(f.info.length), 2) if f else 0.0
        except Exception:
            return 0.0

    # ==================== 返回包装 ====================

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