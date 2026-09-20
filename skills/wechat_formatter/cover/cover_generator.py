# skills/wechat_formatter/cover/cover_generator.py
"""公众号封面图生成器（用 dispatcher.generate_image）。"""

import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

COVER_PROMPT_TEMPLATE = """请创建一张吸引眼球的公众号封面图，遵循以下规范：

视觉风格
- Notion 插画风格，比例为 2.35:1（公众号封面标准尺寸）
- 色彩鲜明、对比强烈，确保在小尺寸预览时依然醒目
- 风格统一，避免写实元素，保持整体手绘质感

构图要求
- 主视觉元素居中或偏左（右侧预留标题区域）
- 添加 1-2 个简洁的卡通形象、图标或人物剪影，增强记忆点
- 大量留白，突出核心信息，避免画面拥挤

文字处理
- 标题文字大而醒目，控制在 8 字以内
- 可添加 1 行副标题或关键词标签
- 字体风格与手绘插画协调统一

语言
- 默认使用中文
- 画面内所有可读文字必须使用简体中文

内容主题：{topic}
封面标题：{title}"""


class CoverGenerator:
    """公众号封面图生成器。"""

    def __init__(self, output_dir: str = "./data/assets/wechat/covers"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        title: str,
        topic: str,
        output_path: str = "",
    ) -> str:
        """生成封面图，返回本地路径。"""
        from engines import dispatcher

        prompt = COVER_PROMPT_TEMPLATE.format(title=title, topic=topic)

        logger.info("🎨 生成封面图...")
        img, used = await dispatcher.generate_image(
            prompt=prompt,
            width=1280,
            height=720,
        )
        logger.info(f"封面图引擎={used}")

        if output_path:
            dst = Path(output_path)
        else:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = re.sub(r"[^\w\u4e00-\u9fff-]", "", title[:20]) or "cover"
            dst = self.output_dir / f"{ts}_cover_{safe}.png"

        dst.parent.mkdir(parents=True, exist_ok=True)
        img.save(dst, "PNG")
        logger.info(f"✅ 封面已保存: {dst}")
        return str(dst)

    def generate_sync(self, title: str, topic: str, output_path: str = "") -> str:
        """同步版本（给 CLI 或非 async 场景用）。"""
        return asyncio.run(self.generate(title, topic, output_path))