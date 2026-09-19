# server/api/v1/skills.py
"""Skills API：列出、执行。

设计：
    - 同步接口（skills 都快，不需要 job 体系）
    - 静态注册表，新增 skill 时这里加一行
    - 执行结果里的本地路径自动转成 /files/xxx URL
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from server.core.config import settings

router = APIRouter()


# ==================== 注册表 ====================

SKILL_REGISTRY: dict[str, dict] = {
    "voice_assistant": {
        "name": "语音合成",
        "description": "文字转语音（edge-tts）",
        "version": "1.0.0",
        "actions": [
            {
                "id": "tts",
                "name": "文字转语音",
                "params": [
                    {"name": "text", "type": "string", "required": True,
                     "description": "要合成的文本"},
                    {"name": "voice", "type": "string",
                     "default": "zh-CN-XiaoxiaoNeural"},
                    {"name": "speed", "type": "number",
                     "default": 1.0, "min": 0.5, "max": 2.0},
                    {"name": "auto_split", "type": "boolean", "default": False},
                ],
            },
            {
                "id": "list_voices",
                "name": "列出语音",
                "params": [],
            },
        ],
    },
    "music_generator": {
        "name": "音乐生成",
        "description": "纯规则 MIDI 生成（不含神经网络模型）",
        "version": "3.0.0",
        "actions": [
            {
                "id": "compose_midi",
                "name": "生成 MIDI",
                "params": [
                    {"name": "topic", "type": "string", "default": "星辰大海"},
                    {"name": "emotion", "type": "string", "default": "epic"},
                    {"name": "duration", "type": "integer",
                     "default": 30, "min": 5, "max": 300},
                    {"name": "arrangement", "type": "string",
                     "default": "symphony"},
                    {"name": "complexity", "type": "integer",
                     "default": 1, "min": 1, "max": 3},
                    {"name": "with_lyrics", "type": "boolean", "default": False},
                    {"name": "language", "type": "string", "default": "zh"},
                ],
            },
            {
                "id": "list_options",
                "name": "列出选项",
                "params": [],
            },
        ],
    },
}


# ==================== 请求体 ====================

class SkillExecuteRequest(BaseModel):
    action: str = Field(..., description="skill 内的子操作 id")
    params: dict[str, Any] = Field(default_factory=dict, description="子操作参数")


# ==================== 路由 ====================

@router.get("")
async def list_skills():
    """列出所有可用 skills。"""
    return [
        {
            "id": k,
            "name": v["name"],
            "description": v["description"],
            "version": v["version"],
            "actions": v["actions"],
        }
        for k, v in SKILL_REGISTRY.items()
    ]


@router.get("/{skill_name}")
async def get_skill(skill_name: str):
    """单个 skill 详情。"""
    if skill_name not in SKILL_REGISTRY:
        raise HTTPException(404, f"未知 skill: {skill_name}")
    return {"id": skill_name, **SKILL_REGISTRY[skill_name]}


@router.post("/{skill_name}/execute")
async def execute_skill(skill_name: str, req: SkillExecuteRequest):
    """执行 skill action（同步）。"""
    if skill_name not in SKILL_REGISTRY:
        raise HTTPException(404, f"未知 skill: {skill_name}")

    skill = _load_skill(skill_name)
    if skill is None:
        raise HTTPException(500, f"skill 加载失败: {skill_name}")

    # 合并参数
    kwargs = {"action": req.action, **req.params}

    try:
        result = await skill.execute(**kwargs)
    except Exception as e:
        raise HTTPException(500, f"skill 执行失败: {e}")

    # 把本地路径转成 /files/xxx
    _normalize_paths(result)

    return result


# ==================== 内部 ====================

_SKILL_INSTANCES: dict[str, Any] = {}


def _load_skill(name: str):
    """懒加载并缓存 skill 实例。"""
    if name in _SKILL_INSTANCES:
        return _SKILL_INSTANCES[name]

    try:
        if name == "voice_assistant":
            from skills.voice_assistant import VoiceAssistant
            inst = VoiceAssistant()
        elif name == "music_generator":
            from skills.music_generator import MusicMaestro
            inst = MusicMaestro()
        else:
            return None
    except Exception:
        return None

    _SKILL_INSTANCES[name] = inst
    return inst


# 需要转 URL 的字段名
_PATH_FIELDS = {
    "audio_path", "audio_paths",
    "midi_path", "lyrics_path",
    "segment_files",
}


def _path_to_url(path: str) -> str:
    """把 data/assets 下的路径转成 /files/{key}。"""
    p = Path(path).resolve()
    root = settings.storage_local_dir.resolve()
    try:
        rel = p.relative_to(root)
        return f"/files/{rel.as_posix()}"
    except ValueError:
        return path


def _normalize_paths(result: dict) -> None:
    """原地递归，把路径字段转成 URL。"""
    def _walk(d):
        if isinstance(d, dict):
            for k, v in list(d.items()):
                if k in _PATH_FIELDS:
                    if isinstance(v, str):
                        d[k] = _path_to_url(v)
                    elif isinstance(v, list):
                        d[k] = [
                            _path_to_url(x) if isinstance(x, str) else x
                            for x in v
                        ]
                else:
                    _walk(v)
        elif isinstance(d, list):
            for item in d:
                _walk(item)

    _walk(result)