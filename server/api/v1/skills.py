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

    "novel_writer": {
        "name": "小说生成",
        "description": "多语言小说生成 + 断点续写（走 dispatcher.chat）",
        "version": "2.0.0",
        "actions": [
            {
                "id": "generate",
                "name": "生成小说",
                "params": [
                    {"name": "title", "type": "string", "required": True,
                     "description": "小说标题"},
                    {"name": "genre", "type": "string", "required": True,
                     "description": "类型（如：科幻 / 奇幻 / 悬疑）"},
                    {"name": "outline", "type": "string", "required": True,
                     "description": "故事大纲"},
                    {"name": "characters", "type": "string", "required": True,
                     "description": "角色设定"},
                    {"name": "chapter_count", "type": "integer",
                     "default": 3, "min": 1, "max": 20},
                    {"name": "words_per_chapter", "type": "integer",
                     "default": 500, "min": 200, "max": 2000},
                    {"name": "language", "type": "string", "default": "zh",
                     "description": "zh/en/ja/es/fr/de/it/pt/ko/ar/th/nl/pl/sv/fi/el/he/hi"},
                    {"name": "style", "type": "string", "default": "细腻"},
                    {"name": "temperature", "type": "number",
                     "default": 0.85, "min": 0.0, "max": 1.0},
                ],
            },
            {
                "id": "continue",
                "name": "续写",
                "params": [
                    {"name": "file", "type": "string", "required": True,
                     "description": "已有小说文件的本地路径或 URL"},
                    {"name": "chapter_count", "type": "integer",
                     "default": 3, "min": 1, "max": 20},
                ],
            },
            {
                "id": "list_languages",
                "name": "列出语言",
                "params": [],
            },
        ],
    }, 
    
    "tech_hot_article": {
        "name": "技术热点文章",
        "description": "抓取技术热点 + LLM 写稿 + AI 配图 + Word 导出",
        "version": "2.0.0",
        "actions": [
            {
                "id": "list_hot",
                "name": "列出热点",
                "params": [],
            },
            {
                "id": "generate",
                "name": "生成文章",
                "params": [
                    {"name": "hot_index", "type": "integer",
                     "description": "选择第几条热点（不填则随机）"},
                    {"name": "style", "type": "string", "default": "",
                     "description": "写作风格（不填则随机）：专业分析型 / 通俗科普型 / 深度技术型 / 行业观察型 / 趋势预测型"},
                    {"name": "article_words", "type": "integer", "default": 1500},
                    {"name": "with_images", "type": "boolean", "default": True},
                ],
            },
        ],
    },  
    
    "news_aggregator": {
        "name": "新闻聚合",
        "description": "RSS 新闻抓取 + 去重 + AI 摘要（可选）",
        "version": "2.0.0",
        "actions": [
            {
                "id": "list_feeds",
                "name": "列出新闻源",
                "params": [],
            },
            {
                "id": "fetch",
                "name": "抓取新闻",
                "params": [
                    {"name": "category", "type": "string", "default": "",
                     "description": "分类：tech / business / world / china / japan / korea / usa（不填=全部）"},
                    {"name": "sources", "type": "string", "default": "",
                     "description": "自定义源关键词（逗号分隔，如：nhk,bbc）"},
                    {"name": "top_n", "type": "integer", "default": 50},
                    {"name": "validate", "type": "boolean", "default": True,
                     "description": "是否验证 RSS 源可用性（首次慢，之后有缓存）"},
                    {"name": "with_summary", "type": "boolean", "default": False,
                     "description": "是否生成 AI 摘要（消耗 LLM）"},
                ],
            },
        ],
    }, 

    "image_curator": {
        "name": "图片鉴赏",
        "description": "用视觉模型给一组图片写鉴赏描述，生成图文文章",
        "version": "2.0.0",
        "actions": [
            {
                "id": "curate",
                "name": "生成鉴赏文章",
                "params": [
                    {"name": "directory", "type": "string", "default": "",
                     "description": "服务器本地目录（本机用）"},
                    {"name": "image_urls", "type": "list", "default": [],
                     "description": "图片 URL 列表（Web 用，如 ['/files/xxx.png']）"},
                    {"name": "title", "type": "string", "default": ""},
                    {"name": "intro", "type": "string", "default": ""},
                    {"name": "recursive", "type": "boolean", "default": False},
                    {"name": "max_images", "type": "integer", "default": 100},
                    {"name": "with_intro", "type": "boolean", "default": True},
                ],
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
        elif name == "novel_writer":                        # ← 新增
            from skills.novel_writer import NovelWriter
            inst = NovelWriter()  
            
        elif name == "tech_hot_article":
            from skills.tech_hot_article import TechHotArticle
            inst = TechHotArticle()   
            
        elif name == "news_aggregator":
            from skills.news_aggregator import NewsAggregator
            inst = NewsAggregator()   

        elif name == "image_curator":
            from skills.image_curator import ImageCurator
            inst = ImageCurator()            
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