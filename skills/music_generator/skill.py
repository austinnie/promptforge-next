# skills/music_generator/skill.py
"""音乐生成 skill（纯 MIDI，不含神经网络模型）。

能力：
    compose_midi   根据情绪 / 编曲 / 时长生成 MIDI 文件
    list_options   列出可用的情绪 / 编曲 / 乐器

说明：
    - 输出是 .mid 文件，用户需自备 MIDI 播放器或用 DAW 打开
    - 不做 MP3 合成（需要 SoundFont + FluidSynth + 大体积二进制）
    - 歌词可选，由 dispatcher.chat 生成
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import ARRANGEMENTS, EMOTION_CONFIG, INSTRUMENTS
from .engine import MidiEngine

logger = logging.getLogger(__name__)


class MusicMaestro:
    """音乐生成器（MIDI 版）。"""

    NAME = "music_generator"
    VERSION = "3.0.0"   # 跟老项目 v2 区分（去掉 MusicGen）

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.output_dir = Path(
            self.config.get("output_dir", "./data/assets/music")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.engine = MidiEngine(seed=self.config.get("seed"))

    # ==================== 主入口 ====================

    async def execute(self, **kwargs) -> dict:
        action = kwargs.pop("action", "compose_midi")     # ← 用 pop
        try:
            if action == "list_options":
                return self._ok(self._list_options())
            if action == "compose_midi":
                return self._ok(await self._compose(**kwargs))
            return self._err(f"未知 action: {action}")
        except Exception as e:
            logger.exception("MusicMaestro 执行失败")
            return self._err(str(e))

    # ==================== 生成 ====================

    async def _compose(
        self,
        topic: str = "星辰大海",
        emotion: str = "epic",
        duration: int = 30,
        arrangement: str = "symphony",
        complexity: int = 1,
        with_lyrics: bool = False,
        language: str = "zh",     # ← 新增
    ) -> dict:
        if emotion not in EMOTION_CONFIG:
            raise ValueError(
                f"未知情绪 {emotion}，可选: {list(EMOTION_CONFIG)}"
            )
        if arrangement not in ARRANGEMENTS:
            raise ValueError(
                f"未知编曲 {arrangement}，可选: {list(ARRANGEMENTS)}"
            )

        duration = max(5, min(int(duration), 300))
        complexity = max(1, min(int(complexity), 3))

        # 1. 生成 MIDI 字节
        midi_bytes = self.engine.generate(
            emotion=emotion,
            duration=duration,
            arrangement=arrangement,
            complexity=complexity,
        )

        # 2. 保存
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = re.sub(r"[^\w\u4e00-\u9fff-]", "_", topic)[:20] or "untitled"
        filename = f"{safe_topic}_{emotion}_{arrangement}_{ts}.mid"
        out_path = self.output_dir / filename
        out_path.write_bytes(midi_bytes)

        result: dict[str, Any] = {
            "midi_path": str(out_path),
            "size_bytes": len(midi_bytes),
            "topic": topic,
            "emotion": emotion,
            "emotion_name": EMOTION_CONFIG[emotion]["name"],
            "arrangement": arrangement,
            "arrangement_name": ARRANGEMENTS[arrangement]["name"],
            "duration": duration,
            "complexity": complexity,
            "tracks": len(ARRANGEMENTS[arrangement]["tracks"]),
            "note": "输出为 MIDI 文件，需使用 MIDI 播放器或 DAW 打开",
        }

        # 3. 歌词（可选）
        # 3. 歌词（可选）
        if with_lyrics:
            lyrics, used_engine = await self._generate_lyrics(
                topic, emotion, language
            )
            result["lyrics"] = lyrics
            result["lyrics_engine"] = used_engine

            lyrics_path = out_path.with_suffix(".json")
            lyrics_path.write_text(
                json.dumps(lyrics, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            result["lyrics_path"] = str(lyrics_path)

        return result

    # ==================== 歌词 ====================

    async def _generate_lyrics(
        self, topic: str, emotion: str, language: str,
    ) -> tuple[dict, str]:
        """调 dispatcher.chat 生成歌词，失败则回退到模板。"""
        emo_name = EMOTION_CONFIG.get(emotion, {}).get("name", emotion)

        prompt = (
            f"创作一首关于「{topic}」的{emo_name}风格歌词，语言：{language}。\n"
            f"只返回 JSON，格式：\n"
            f'{{"title": "标题", "structure": '
            f'{{"verse": ["主歌1", "主歌2"], "chorus": ["副歌"], "bridge": ["桥段"]}}, '
            f'"vocal_style": "风格"}}'
        )

        try:
            from engines import dispatcher
            text, used = await dispatcher.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=800,
            )
            data = self._parse_json(text)
            if data and "structure" in data:
                return data, used
        except Exception as e:
            logger.warning(f"歌词生成失败，使用模板: {e}")

        # 模板回退
        return {
            "title": f"{topic}之歌",
            "structure": {
                "verse": [
                    f"在{emo_name}的光辉中，",
                    f"我听见{topic}的呼唤",
                ],
                "chorus": [
                    f"{topic}，如此{emo_name}，",
                    f"照亮我前行的路",
                ],
                "bridge": [
                    "当星光洒落，",
                    "我依然能听见那首歌",
                ],
            },
            "vocal_style": "空灵治愈" if emotion == "peaceful" else "力量激昂",
        }, "fallback_template"

    @staticmethod
    def _parse_json(text: str) -> Optional[dict]:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            return None

    # ==================== 选项 ====================

    def _list_options(self) -> dict:
        return {
            "emotions": [
                {"id": k, "name": v["name"], "tempo": v["tempo"]}
                for k, v in EMOTION_CONFIG.items()
            ],
            "arrangements": [
                {
                    "id": k,
                    "name": v["name"],
                    "description": v["description"],
                    "mood": v["mood"],
                    "instrument_count": len(v["tracks"]),
                }
                for k, v in ARRANGEMENTS.items()
            ],
            "instruments": [
                {"id": k, "name": v["name"], "family": v["family"]}
                for k, v in INSTRUMENTS.items()
            ],
        }

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