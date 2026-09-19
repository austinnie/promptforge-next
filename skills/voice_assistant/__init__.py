# skills/voice_assistant/__init__.py
"""语音助手：TTS（edge-tts）+ 长文本分段 + ffmpeg 合并。"""

from .skill import VoiceAssistant

__all__ = ["VoiceAssistant"]