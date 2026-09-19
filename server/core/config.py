# server/core/config.py
"""全局配置（pydantic-settings）。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 部署 ----
    deployment: str = "local"
    host: str = "127.0.0.1"
    port: int = 8000

    # ---- 存储 ----
    storage_backend: str = "local"
    storage_local_dir: Path = Path("./data/assets")

    # ---- 数据库（P3 先不用） ----
    db_backend: str = "sqlite"
    db_url: str = "sqlite:///./data/db/promptforge.sqlite3"

    # ---- 引擎 keys ----
    agnes_api_key: str = ""
    agnes_base_url: str = ""
    agnes_image_model: str = "agnes-image-2.1-flash"
    agnes_video_model: str = "agnes-video-2.5-flash"
    agnes_text_model: str = "agnes-2.5-flash"
    agnes_vision_model: str = "agnes-2.5-flash"

    pollinations_api_key: str = ""
    pollinations_model: str = "black-forest-labs/flux.1-schnell"

    siliconflow_api_key: str = ""
    siliconflow_model: str = "sd-turbo"

    openrouter_api_key: str = ""
    openrouter_model: str = "bytedance-seed/seedream-4.5"

    # ---- LLM ----
    llm_enabled: bool = False
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:1.5b"

    # ---- 安全 ----
    safe_mode: bool = True
    enable_safety_check: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()