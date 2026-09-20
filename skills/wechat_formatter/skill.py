# skills/wechat_formatter/skill.py
"""wechat_formatter - 微信公众号排版。

能力：
    format           Markdown → 微信 HTML（单主题/画廊）
    generate_cover   生成封面图
    publish          推送到草稿箱（需要微信 AppID/Secret）
    list_themes      列出所有主题

改造点：
    - Ollama/api_engines → engines.dispatcher（AI 增强 + 封面）
    - execute 改为 async
    - 输出目录 → data/assets/wechat/
"""

import asyncio
import json
import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from .formatter import engine
from .cover.cover_generator import CoverGenerator
from .publisher.wechat_publish import WechatPublisher

DEFAULT_THEME = "newspaper"


class WechatFormatter:
    """公众号排版技能。"""

    NAME = "wechat_formatter"
    VERSION = "2.0.0"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.output_dir = Path(
            self.config.get("output_dir", "./data/assets/wechat")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.default_theme = self.config.get("default_theme", DEFAULT_THEME)
        self._cover = CoverGenerator(str(self.output_dir / "covers"))
        self._publisher = WechatPublisher()

    # ==================== 主入口 ====================

    async def execute(self, **kwargs) -> dict:
        action = kwargs.pop("action", "format")
        try:
            if action == "format":
                return self._ok(await self._format(**kwargs))
            if action == "generate_cover":
                return self._ok(await self._generate_cover(**kwargs))
            if action == "publish":
                return self._ok(await asyncio.to_thread(self._publish, **kwargs))
            if action == "list_themes":
                return self._ok(self._list_themes())
            return self._err(f"未知 action: {action}")
        except Exception as e:
            logger.exception("WechatFormatter 执行失败")
            return self._err(str(e))

    # ==================== format ====================

    async def _format(
        self,
        input: str = "",
        content: str = "",
        theme: str = "",
        gallery: bool = False,
        enhance: bool = False,
        recommend: Optional[list] = None,
        footer_image: str = "",
        footer_alt: str = "关注",
    ) -> dict:
        start = time.time()

        # 1. 获取 Markdown
        if not content:
            if not input:
                raise ValueError("必须提供 input（文件路径）或 content（Markdown 文本）")
            p = Path(input)
            if not p.exists():
                raise FileNotFoundError(f"文件不存在: {input}")
            content = p.read_text(encoding="utf-8")
            input_path = p
        else:
            # 直接文本：从第一行标题里取文件名
            first_line = content.strip().split("\n", 1)[0]
            fname = re.sub(r"[^\w\u4e00-\u9fff _-]", "",
                           first_line.lstrip("# ")[:30]).strip()
            if not fname:
                fname = "inline"
            input_path = self.output_dir / f"{fname}.md"

        # 2. 可选 AI 增强
        if enhance:
            content = await self._ai_enhance(content)

        # 3. 追加文末引导图
        if footer_image:
            fp = Path(footer_image)
            if fp.exists():
                content = content.rstrip() + f"\n\n---\n\n![{footer_alt}]({fp.as_posix()})\n"
            else:
                logger.warning(f"文末引导图不存在: {footer_image}")

        # 4. 输出目录
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe = re.sub(r"[^\w\u4e00-\u9fff _-]", "",
                      input_path.stem[:40]).strip() or "article"
        out_dir = self.output_dir / f"{ts}_{safe}"
        out_dir.mkdir(parents=True, exist_ok=True)

        # 5. 排版（重逻辑走 to_thread）
        result = await asyncio.to_thread(
            self._format_sync,
            content, input_path, out_dir,
            theme or self.default_theme,
            gallery,
            recommend or [],
        )

        result["elapsed"] = f"{time.time() - start:.2f}s"
        return result

    def _format_sync(
        self, content: str, input_path: Path, out_dir: Path,
        theme_name: str, gallery: bool, recommend: list,
    ) -> dict:
        """同步排版（原 skill.py 逻辑）。"""
        # 预处理
        content = engine.strip_frontmatter(content)
        content = engine.fix_cjk_spacing(content)
        content = engine.fix_cjk_bold_punctuation(content)
        content = engine.process_callouts(content)
        content = engine.process_manual_footnotes(content)
        content = engine.process_fenced_containers(content)
        content = re.sub(r"~~(.+?)~~", r"<del>\1</del>", content)

        content = engine.convert_wikilinks(content, engine.VAULT_ROOT, out_dir)
        content = engine.copy_markdown_images(content, input_path.parent, out_dir)

        html = engine.md_to_html(content)
        html, footnote_html = engine.extract_links_as_footnotes(html)

        title = engine.extract_title(content, input_path)
        word_count = engine.count_words(content)

        # 画廊模式
        if gallery:
            theme_map = {}
            for tid in engine.GALLERY_THEMES:
                tp = engine.THEMES_DIR / f"{tid}.json"
                if tp.exists():
                    theme_map[tid] = json.loads(tp.read_text(encoding="utf-8"))
            theme_ids = [t for t in engine.GALLERY_THEMES if t in theme_map]

            rendered_map = {}
            for tid in theme_ids:
                rendered = engine.inject_inline_styles(html, theme_map[tid])
                rendered = engine.convert_image_captions(rendered)
                if footnote_html:
                    fn = engine.inject_inline_styles(
                        footnote_html, theme_map[tid], skip_wrapper=True
                    )
                    rendered += "\n" + fn
                rendered_map[tid] = rendered

            gallery_path = engine.generate_gallery(
                rendered_map, theme_map, theme_ids,
                title, word_count, out_dir, recommended=recommend,
            )
            return {
                "mode": "gallery",
                "gallery_path": self._to_url(str(gallery_path)),
                "article_dir": str(out_dir),
                "title": title,
                "word_count": word_count,
                "theme_count": len(theme_ids),
            }

        # 单主题
        theme = engine.load_theme(theme_name)
        html = engine.inject_inline_styles(html, theme)
        if footnote_html:
            footnote_html = engine.inject_inline_styles(
                footnote_html, theme, skip_wrapper=True
            )

        html = engine.convert_image_captions(html)
        if footnote_html:
            footnote_html = engine.convert_image_captions(footnote_html)

        full = html
        if footnote_html:
            full += "\n" + footnote_html

        article_path = out_dir / "article.html"
        article_path.write_text(full, encoding="utf-8")

        preview_path = out_dir / "preview.html"
        engine.generate_preview(
            html, footnote_html, theme, title, word_count, preview_path
        )

        return {
            "mode": "single",
            "title": title,
            "word_count": word_count,
            "theme": theme_name,
            "theme_name": theme.get("name", theme_name),
            "article_path": self._to_url(str(article_path)),
            "preview_path": self._to_url(str(preview_path)),
            "article_dir": str(out_dir),
        }

    # ==================== cover ====================

    async def _generate_cover(
        self, title: str = "", topic: str = "", output_path: str = "",
    ) -> dict:
        if not title:
            raise ValueError("title 不能为空")
        topic = topic or title
        path = await self._cover.generate(title, topic, output_path)
        return {
            "cover_path": self._to_url(path),
            "local_path": path,
        }

    # ==================== publish ====================

    def _publish(self, article_dir: str = "", cover_path: str = "", title: str = "") -> dict:
        if not self._publisher.is_configured():
            raise RuntimeError(
                "未配置微信凭证。请在 .env 里设置 "
                "WECHAT_APP_ID 和 WECHAT_APP_SECRET"
            )
        return self._publisher.publish(
            article_dir=article_dir,
            cover_path=cover_path,
            title=title,
        )

    # ==================== AI 增强 ====================

    async def _ai_enhance(self, markdown: str) -> str:
        from engines import dispatcher

        prompt = f"""你是微信公众号排版助手。请分析下面的 Markdown 文章，只做结构增强，不改写内容：

规则：
1. 检测到"名字：内容"交替出现的对话 → 用 :::dialogue[标题] ... ::: 包裹
2. 3 张以上连续图片 → 用 :::gallery[标题] ... ::: 包裹
3. 核心观点 → 改成 > [!important] 标题
4. 小技巧 → 改成 > [!tip] 标题
5. 章节之间确保有 --- 分隔

只输出增强后的 Markdown，不要解释。

原文：
{markdown[:6000]}"""

        try:
            text, used = await dispatcher.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=4096,
            )
            logger.info(f"AI 增强引擎={used}")
            return text.strip() or markdown
        except Exception as e:
            logger.warning(f"AI 增强失败，使用原文: {e}")
            return markdown

    # ==================== 主题列表 ====================

    def _list_themes(self) -> dict:
        themes = []
        for p in sorted(engine.THEMES_DIR.glob("*.json")):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                themes.append({
                    "id": p.stem,
                    "name": data.get("name", p.stem),
                    "description": data.get("description", ""),
                })
            except Exception:
                continue
        return {"themes": themes, "count": len(themes)}

    # ==================== 工具 ====================

    def _to_url(self, local_path: str) -> str:
        p = Path(local_path).resolve()
        root = Path("./data/assets").resolve()
        try:
            return f"/files/{p.relative_to(root).as_posix()}"
        except ValueError:
            return local_path

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