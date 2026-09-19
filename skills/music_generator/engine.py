# skills/music_generator/engine.py
"""纯 MIDI 生成引擎（不依赖 SoundFont / FluidSynth / 模型）。

输出：多轨 MIDI 字节流。
"""

import io
import logging
import random
from typing import Optional

from .config import (
    ARRANGEMENTS,
    BASE_NOTE,
    BEAT_PER_CHORD,
    CHORD_PROGRESSIONS,
    EMOTION_CONFIG,
    INSTRUMENTS,
)

logger = logging.getLogger(__name__)


class MidiEngine:
    """多乐器 MIDI 生成器。"""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def generate(
        self,
        emotion: str = "epic",
        duration: int = 30,
        arrangement: str = "symphony",
        complexity: int = 1,
    ) -> bytes:
        """生成 MIDI，返回字节流。"""
        try:
            from midiutil import MIDIFile
        except ImportError:
            raise RuntimeError("midiutil 未安装，请 pip install midiutil")

        arr = ARRANGEMENTS.get(arrangement, ARRANGEMENTS["symphony"])
        emo = EMOTION_CONFIG.get(emotion, EMOTION_CONFIG["peaceful"])
        chords = CHORD_PROGRESSIONS.get(emotion, CHORD_PROGRESSIONS["peaceful"])

        tempo = emo["tempo"]
        scale = emo["scale"]
        tracks = arr["tracks"]

        midi = MIDIFile(len(tracks))
        for idx, t in enumerate(tracks):
            self._render_track(
                midi, idx, t, chords, scale,
                duration, tempo, complexity,
            )

        buf = io.BytesIO()
        midi.writeFile(buf)
        return buf.getvalue()

    # ---------- 单轨渲染 ----------

    def _render_track(
        self, midi, track_idx, track_info,
        chords, scale, duration, tempo, complexity,
    ):
        inst_name = track_info.get("instrument", "")
        inst = INSTRUMENTS.get(inst_name)
        if not inst:
            logger.warning(f"未知乐器: {inst_name}")
            return

        role = track_info.get("role", "旋律")
        offset = int(track_info.get("octave_offset", 0))
        volume = int(track_info.get("volume", 85))

        midi.addTempo(track_idx, 0, tempo)
        midi.addProgramChange(track_idx, 0, 0, inst["program"])

        total_beats = duration * (tempo / 60.0)
        density = 1.0 + (complexity - 1) * 0.3

        if role in ("主旋律", "旋律", "第一小提琴", "高音"):
            self._emit_melody(
                midi, track_idx, chords, scale, offset,
                total_beats, volume, density,
            )
        elif role in ("和弦", "和声", "伴奏"):
            self._emit_chord(
                midi, track_idx, chords, offset, total_beats, volume,
            )
        elif role in ("低音", "根音"):
            self._emit_bass(
                midi, track_idx, chords, offset, total_beats, volume,
            )
        elif role == "打击":
            self._emit_percussion(
                midi, track_idx, offset, total_beats, volume,
            )
        else:
            self._emit_ornament(
                midi, track_idx, chords, scale, offset,
                total_beats, volume, density,
            )

    # ---------- 各种角色 ----------

    def _emit_melody(
        self, midi, track, chords, scale, offset, total_beats, volume, density,
    ):
        current = 0.0
        chord_idx = 0
        while current < total_beats:
            chord_len = min(BEAT_PER_CHORD, total_beats - current)
            sub = 0.0
            while sub < chord_len and current + sub < total_beats:
                note = self._rng.choice(scale)
                octave = offset + (12 if self._rng.random() < 0.3 else 0)
                pitch = BASE_NOTE + note + octave
                dur = self._rng.choice([0.5, 0.5, 1.0, 0.25]) * density
                if 0 <= pitch <= 127:
                    midi.addNote(
                        track, 0, pitch,
                        current + sub, dur, volume,
                    )
                sub += dur
            chord_idx += 1
            current += chord_len

    def _emit_chord(self, midi, track, chords, offset, total_beats, volume):
        current = 0.0
        idx = 0
        while current < total_beats:
            chord = chords[idx % len(chords)]
            dur = min(BEAT_PER_CHORD, total_beats - current)
            for note in chord:
                pitch = BASE_NOTE + note + offset
                if 0 <= pitch <= 127:
                    midi.addNote(
                        track, 0, pitch, current, dur, int(volume * 0.9),
                    )
            idx += 1
            current += dur

    def _emit_bass(self, midi, track, chords, offset, total_beats, volume):
        current = 0.0
        idx = 0
        while current < total_beats:
            chord = chords[idx % len(chords)]
            dur = min(BEAT_PER_CHORD, total_beats - current)
            root = BASE_NOTE + chord[0] + offset
            if 0 <= root <= 127:
                midi.addNote(
                    track, 0, root, current, dur, int(volume * 0.9),
                )
            idx += 1
            current += dur

    def _emit_percussion(self, midi, track, offset, total_beats, volume):
        beat = 0.0
        while beat < total_beats:
            if int(beat) % 2 == 0:
                pitch = BASE_NOTE + 47 + offset   # 定音鼓附近
                if 0 <= pitch <= 127:
                    midi.addNote(track, 0, pitch, beat, 0.5, int(volume * 0.9))
            beat += 1.0

    def _emit_ornament(
        self, midi, track, chords, scale, offset, total_beats, volume, density,
    ):
        beat = 0.0
        while beat < total_beats:
            if self._rng.random() < 0.2 * density:
                note = self._rng.choice(scale)
                pitch = BASE_NOTE + note + offset
                dur = self._rng.choice([0.25, 0.5])
                if 0 <= pitch <= 127:
                    midi.addNote(
                        track, 0, pitch, beat, dur, int(volume * 0.7),
                    )
            beat += 0.5