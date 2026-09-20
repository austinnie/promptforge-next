# skills/image_curator/skill.py
"""图片鉴赏文章生成 skill。

能力：
    curate  对一组图片做 vision 鉴赏，生成图文混排文章

图片输入（二选一）：
    - directory:    服务器本地目录（CLI / 本机用）
    - image_urls:   URL 列表（API / Web 用）

输出：
    - article.md            （总是）
    - article.html          （可选，默认开）
    - article.docx          （可选，装了 python-docx 就有）
    - article.print.html    （可选，浏览器 Ctrl+P → PDF）
    - clipboard.html        （可选，微信/知乎富文本）
    - metadata.json         （总是，含全部条目）
"""

import asyncio
import html
import json
import logging
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests
from PIL import Image

from .writers import ClipboardWriter, PrintWriter, WordWriter, make_heading

logger = logging.getLogger(__name__)

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

DEFAULT_DESCRIPTION_PROMPT = (
    "请详细描述这张图片。"
    "涵盖主体、构图、色彩、光影、风格、氛围等方面；"
    "用流畅优雅的中文写作；"
    "150 字左右。"
    "只输出描述正文，不要分点、不要标题、不要评价语。"
)

_FALLBACK_PROMPT = (
    "请用流畅的中文详细描述这张图片，150 字左右，"
    "涵盖主体、构图、色彩、风格、氛围。只输出正文。"
)


class ImageCurator:
    """图片鉴赏文章生成器。"""

    NAME = "image_curator"
    VERSION = "2.0.0"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

        self.output_dir = Path(
            self.config.get("output_dir", "./data/assets/curator")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 下载远程图片时用的临时目录
        self.cache_dir = Path(
            self.config.get("cache_dir", "./data/cache/curator")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_images = int(self.config.get("max_images", 100))
        self.throttle_seconds = float(self.config.get("throttle_seconds", 2))
        self.vision_max_size = int(self.config.get("vision_max_size", 1280))
        self.description_prompt = self.config.get(
            "description_prompt", DEFAULT_DESCRIPTION_PROMPT
        )
        self.author = self.config.get("author", "AI 艺术评论")

        # 输出开关
        self.gen_html = bool(self.config.get("generate_html", True))
        self.gen_docx = bool(self.config.get("generate_docx", True))
        self.gen_print = bool(self.config.get("generate_print", True))
        self.gen_clipboard = bool(self.config.get("generate_clipboard", True))

    # ==================== 主入口 ====================

    async def execute(self, **kwargs) -> dict:
        action = kwargs.pop("action", "curate")
        try:
            if action == "curate":
                return self._ok(await self._curate(**kwargs))
            return self._err(f"未知 action: {action}")
        except Exception as e:
            logger.exception("ImageCurator 执行失败")
            return self._err(str(e))

    async def _curate(
        self,
        directory: str = "",
        image_urls: Optional[list[str]] = None,
        title: str = "",
        intro: str = "",
        recursive: bool = False,
        max_images: Optional[int] = None,
        with_intro: bool = True,
    ) -> dict:
        start = time.time()

        # 1. 收集图片
        sources = self._collect_sources(directory, image_urls, recursive)
        if not sources:
            raise ValueError("未找到任何图片（directory 或 image_urls 至少一个）")

        max_n = max_images if max_images is not None else self.max_images
        sources = sources[:max_n]
        logger.info(f"共 {len(sources)} 张图片")

        # 2. 逐张分析
        entries: list[dict[str, Any]] = []
        for idx, (src_type, src_value) in enumerate(sources, 1):
            logger.info(f"[{idx}/{len(sources)}] {src_value}")
            entry = await self._analyze_image(src_type, src_value, idx)
            entries.append(entry)
            if idx < len(sources):
                await asyncio.sleep(self.throttle_seconds)

        # 3. 准备输出目录
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r"[^\w\u4e00-\u9fff _-]", "", title or "gallery")
        safe_title = safe_title.strip() or "gallery"
        article_dir = self.output_dir / f"{ts}_{safe_title}"
        assets_dir = article_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        # 4. 把图片拷贝/下载到 assets/
        for e in entries:
            try:
                dst = assets_dir / e["filename"]
                src = Path(e["local_path"])
                if src.exists() and src.resolve() != dst.resolve():
                    shutil.copy2(src, dst)
                e["asset_path"] = f"assets/{e['filename']}"
            except Exception as ex:
                logger.warning(f"拷贝失败 {e['filename']}: {ex}")
                e["asset_path"] = ""

        # 5. 引言
        final_title = title or Path(directory).name if directory else (title or "作品集")
        final_intro = intro.strip()
        if not final_intro and with_intro:
            final_intro = await self._generate_intro(final_title, entries)
        if not final_intro:
            final_intro = f"本文收录了「{final_title}」主题下的 {len(entries)} 张作品。"

        # 6. 写文件
        md_path = article_dir / "article.md"
        self._write_markdown(md_path, final_title, final_intro, entries)

        html_path = None
        if self.gen_html:
            html_path = article_dir / "article.html"
            self._write_html(html_path, final_title, final_intro, entries)

        docx_path = None
        if self.gen_docx:
            docx_path = article_dir / "article.docx"
            if not WordWriter().write(docx_path, final_title, final_intro, entries):
                docx_path = None

        print_path = None
        if self.gen_print:
            print_path = article_dir / "article.print.html"
            PrintWriter().write(print_path, final_title, final_intro, entries)

        clipboard_path = None
        if self.gen_clipboard:
            clipboard_path = article_dir / "clipboard.html"
            ClipboardWriter().write(clipboard_path, final_title, final_intro, entries)

        # 7. metadata
        (article_dir / "metadata.json").write_text(
            json.dumps(
                {"title": final_title, "intro": final_intro, "entries": entries},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )

        result = {
            "title": final_title,
            "image_count": len(entries),
            "article_dir": str(article_dir),
            "article_path": self._to_url(str(md_path)),
            "html_path": self._to_url(str(html_path)) if html_path else None,
            "docx_path": self._to_url(str(docx_path)) if docx_path else None,
            "print_path": self._to_url(str(print_path)) if print_path else None,
            "clipboard_path": self._to_url(str(clipboard_path)) if clipboard_path else None,
            "elapsed": f"{time.time() - start:.1f}s",
        }
        logger.info(f"✅ 完成: {len(entries)} 张，{result['elapsed']}")
        return result

    # ==================== 图片来源收集 ====================

    def _collect_sources(
        self, directory: str, image_urls: Optional[list[str]], recursive: bool,
    ) -> list[tuple[str, str]]:
        """返回 [(type, value), ...]，type 是 'local' 或 'url'。"""
        out: list[tuple[str, str]] = []

        if directory:
            d = Path(directory).resolve()
            if not d.exists() or not d.is_dir():
                raise ValueError(f"目录不存在: {d}")
            pattern = "**/*" if recursive else "*"
            for p in sorted(d.glob(pattern)):
                if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                    out.append(("local", str(p)))

        if image_urls:
            for u in image_urls:
                s = (u or "").strip()
                if s:
                    out.append(("url", s))

        return out

    # ==================== 单张分析 ====================

    async def _analyze_image(
        self, src_type: str, src_value: str, index: int,
    ) -> dict[str, Any]:
        """对单张图做 vision 鉴赏。带 3 次重试。"""
        entry: dict[str, Any] = {
            "index": index,
            "filename": "",
            "source_path": src_value,
            "local_path": "",
            "asset_path": "",
            "description": "",
            "error": None,
            "width": None,
            "height": None,
        }

        # 1. 拿到本地文件（URL 就下载）
        try:
            local_path = await asyncio.to_thread(
                self._ensure_local, src_type, src_value,
            )
        except Exception as e:
            entry["filename"] = Path(src_value).name or src_value
            entry["description"] = f"（图片获取失败：{e}）"
            entry["error"] = str(e)
            return entry

        entry["filename"] = Path(local_path).name
        entry["local_path"] = local_path

        # 2. 打开并缩放
        try:
            with Image.open(local_path) as img:
                img.load()
                img = self._resize_for_vision(img, self.vision_max_size)
                entry["width"], entry["height"] = img.size

                # 3. vision 3 次重试
                desc = await self._vision_with_retry(img)
                entry["description"] = desc
                entry["error"] = None
        except Exception as e:
            entry["description"] = f"（鉴赏失败：{e}）"
            entry["error"] = str(e)

        return entry

    def _ensure_local(self, src_type: str, src_value: str) -> str:
        """URL → 下载到 cache；本地 → 直接用。"""
        if src_type == "local":
            return src_value

        # URL
        if src_value.startswith("http://") or src_value.startswith("https://"):
            name = Path(src_value.split("?")[0]).name or "remote"
            safe_name = re.sub(r"[^\w.\-]", "_", name)
            dst = self.cache_dir / f"{int(time.time() * 1000)}_{safe_name}"
            r = requests.get(src_value, timeout=30)
            r.raise_for_status()
            dst.write_bytes(r.content)
            return str(dst)

        # /files/xxx 相对路径（本项目后端返回的格式）
        if src_value.startswith("/files/"):
            # 走本机回环
            base = self.config.get("backend_url", "http://127.0.0.1:8000")
            url = base.rstrip("/") + src_value
            name = Path(src_value).name or "remote"
            safe_name = re.sub(r"[^\w.\-]", "_", name)
            dst = self.cache_dir / f"{int(time.time() * 1000)}_{safe_name}"
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            dst.write_bytes(r.content)
            return str(dst)

        raise ValueError(f"无法处理的图片源: {src_value}")

    async def _vision_with_retry(self, img: Image.Image) -> str:
        """vision 3 次重试，返回描述文本。"""
        from engines import dispatcher

        last_err = ""
        for attempt in range(3):
            prompt = self.description_prompt if attempt == 0 else _FALLBACK_PROMPT
            try:
                text, used = await dispatcher.image_to_text(
                    image=img, prompt=prompt,
                )
                text = (text or "").strip()
                if len(text) >= 50:
                    logger.info(f"vision 引擎={used} 返回 {len(text)} 字")
                    return text
                last_err = f"返回过短 ({len(text)} 字)"
            except Exception as e:
                last_err = str(e)
                logger.warning(f"vision 第 {attempt + 1} 次失败: {e}")
            if attempt < 2:
                await asyncio.sleep(5 * (attempt + 1))

        raise RuntimeError(f"vision 3 次均失败: {last_err}")

    @staticmethod
    def _resize_for_vision(img: Image.Image, max_size: int) -> Image.Image:
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if max(w, h) <= max_size:
            return img
        scale = max_size / max(w, h)
        return img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    # ==================== 引言 ====================

    async def _generate_intro(self, title: str, entries: list[dict]) -> str:
        from engines import dispatcher
        names = "、".join(e["filename"] for e in entries[:5])
        prompt = (
            f"请以艺术评论家的口吻，为标题为「{title}」的作品集写一段 80-120 字的引言，"
            f"概括这组作品的整体气质与看点。\n"
            f"作品集共有 {len(entries)} 张作品，部分文件名：{names}。\n"
            f"注意：这只是根据标题和数量写一段介绍性文字，"
            f"你不需要查看任何图片，直接根据标题想象并写出引言。\n"
            f"只输出正文，不要标题，不要用'抱歉'之类的话。"
        )
        try:
            text, used = await dispatcher.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=512,
            )
            logger.info(f"intro 引擎={used}")
            return text.strip()
        except Exception as e:
            logger.warning(f"引言生成失败: {e}")
            return f"本文收录了「{title}」主题下的 {len(entries)} 张作品。"

    # ==================== 各格式输出 ====================

    def _write_markdown(self, path: Path, title: str, intro: str, entries: list[dict]):
        lines = [
            f"# {title}",
            "",
            f"> 共 {len(entries)} 张作品 · 生成于 {datetime.now():%Y-%m-%d %H:%M}",
            "",
            intro,
            "",
            "---",
            "",
        ]
        for e in entries:
            heading = make_heading(e)
            lines.append(f"## {e['index']}. {heading}")
            lines.append("")
            if e.get("asset_path"):
                lines.append(f"![{heading}]({e['asset_path']})")
                lines.append("")
            lines.append(e["description"])
            lines.append("")
            lines.append("---")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _write_html(self, path: Path, title: str, intro: str, entries: list[dict]):
        esc_title = html.escape(title)
        esc_intro = html.escape(intro)

        articles = []
        for e in entries:
            heading = html.escape(make_heading(e))
            asset = html.escape(e.get("asset_path") or "")
            desc = html.escape(e["description"])
            filename = html.escape(e["filename"])
            articles.append(f"""
    <article class="entry">
      <div class="entry-index">{e['index']:02d}</div>
      <h2>{heading}</h2>
      <figure><img src="{asset}" alt="{heading}" loading="lazy"></figure>
      <p class="desc">{desc}</p>
      <p class="filename">{filename}</p>
    </article>""")
        body = "\n".join(articles)

        doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc_title}</title>
<style>
  :root {{ --bg:#fafaf7; --fg:#2a2a2a; --muted:#888; --accent:#c25b3b; --rule:#e8e4dc; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; padding:48px 24px 96px; background:var(--bg); color:var(--fg);
          font-family:"Noto Serif SC","Songti SC","STSong",serif; line-height:1.8; }}
  .container {{ max-width:820px; margin:0 auto; }}
  header {{ text-align:center; margin-bottom:64px; }}
  header h1 {{ font-size:2.4em; letter-spacing:.08em; margin:0 0 16px; font-weight:700; }}
  header .meta {{ color:var(--muted); font-size:.9em; }}
  header .intro {{ margin-top:32px; color:#555; font-style:italic;
                   border-top:1px solid var(--rule); border-bottom:1px solid var(--rule);
                   padding:24px 8px; }}
  .entry {{ margin-bottom:72px; position:relative; }}
  .entry-index {{ font-size:3em; color:#e0dbd2; position:absolute; left:-60px; top:-10px;
                  font-family:Georgia,serif; font-style:italic; }}
  .entry h2 {{ font-size:1.5em; margin:0 0 24px; letter-spacing:.02em;
               border-left:3px solid var(--accent); padding-left:16px; }}
  .entry figure {{ margin:0 0 24px; background:#f0ede6; border-radius:4px; overflow:hidden;
                   box-shadow:0 2px 12px rgba(0,0,0,.04); }}
  .entry figure img {{ display:block; width:100%; height:auto; }}
  .entry .desc {{ font-size:1.02em; color:#333; text-align:justify; }}
  .entry .filename {{ color:var(--muted); font-size:.78em;
                      font-family:ui-monospace,Consolas,monospace;
                      margin-top:16px; word-break:break-all; }}
  @media (max-width:640px) {{ body {{ padding:24px 16px 64px; }}
                              .entry-index {{ position:static; margin-bottom:8px; }} }}
</style>
</head>
<body>
  <div class="container">
    <header>
      <h1>{esc_title}</h1>
      <div class="meta">共 {len(entries)} 张作品 · {datetime.now():%Y-%m-%d}</div>
      <div class="intro">{esc_intro}</div>
    </header>
{body}
  </div>
</body>
</html>
"""
        path.write_text(doc, encoding="utf-8")

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