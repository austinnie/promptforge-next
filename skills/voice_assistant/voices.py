# skills/voice_assistant/voices.py
"""edge-tts 常用语音列表（离线回退用）。"""

# 格式：(short_name, locale, gender)
DEFAULT_VOICES = [
    # 中文
    ("zh-CN-XiaoxiaoNeural", "zh-CN", "Female"),
    ("zh-CN-XiaoyiNeural", "zh-CN", "Female"),
    ("zh-CN-YunjianNeural", "zh-CN", "Male"),
    ("zh-CN-YunxiNeural", "zh-CN", "Male"),
    ("zh-CN-YunxiaNeural", "zh-CN", "Male"),
    ("zh-CN-YunyangNeural", "zh-CN", "Male"),
    ("zh-CN-liaoning-XiaobeiNeural", "zh-CN-liaoning", "Female"),
    ("zh-CN-shaanxi-XiaoniNeural", "zh-CN-shaanxi", "Female"),
    ("zh-HK-HiuGaaiNeural", "zh-HK", "Female"),
    ("zh-HK-HiuMaanNeural", "zh-HK", "Female"),
    ("zh-HK-WanLungNeural", "zh-HK", "Male"),
    ("zh-TW-HsiaoChenNeural", "zh-TW", "Female"),
    ("zh-TW-HsiaoYuNeural", "zh-TW", "Female"),
    ("zh-TW-YunJheNeural", "zh-TW", "Male"),
    # 英文
    ("en-US-JennyNeural", "en-US", "Female"),
    ("en-US-AriaNeural", "en-US", "Female"),
    ("en-US-GuyNeural", "en-US", "Male"),
    ("en-US-DavisNeural", "en-US", "Male"),
    ("en-GB-SoniaNeural", "en-GB", "Female"),
    ("en-GB-RyanNeural", "en-GB", "Male"),
    ("en-AU-NatashaNeural", "en-AU", "Female"),
    # 日语
    ("ja-JP-NanamiNeural", "ja-JP", "Female"),
    ("ja-JP-KeitaNeural", "ja-JP", "Male"),
    # 韩语
    ("ko-KR-SunHiNeural", "ko-KR", "Female"),
    ("ko-KR-InJoonNeural", "ko-KR", "Male"),
    # 其他常用
    ("fr-FR-DeniseNeural", "fr-FR", "Female"),
    ("fr-FR-HenriNeural", "fr-FR", "Male"),
    ("de-DE-KatjaNeural", "de-DE", "Female"),
    ("de-DE-ConradNeural", "de-DE", "Male"),
    ("es-ES-ElviraNeural", "es-ES", "Female"),
    ("es-ES-AlvaroNeural", "es-ES", "Male"),
    ("ru-RU-SvetlanaNeural", "ru-RU", "Female"),
    ("pt-BR-FranciscaNeural", "pt-BR", "Female"),
    ("it-IT-ElsaNeural", "it-IT", "Female"),
]

# 按 locale 分组（供前端下拉用）
def voices_by_locale() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for name, locale, _ in DEFAULT_VOICES:
        result.setdefault(locale, []).append(name)
    return result