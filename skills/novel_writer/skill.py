# skills/novel_writer/skill.py
"""小说生成 skill。

能力：
    generate   生成新小说（多语言、多章节）
    continue   断点续写

改造点：
    - 老的本地 Ollama 换成 dispatcher.chat（agnes/pollinations 自动降级）
    - 接口改成 async execute(**kwargs)
    - 输出目录改到 data/assets/novel/
"""

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

from .lang_config import LANG_CONFIG


class NovelWriter:
    """小说生成器（多语言、断点续写）。"""

    NAME = "novel_writer"
    VERSION = "2.0.0"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.output_dir = Path(
            self.config.get("output_dir", "./data/assets/novel")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.default_chapter_count = int(
            self.config.get("default_chapter_count", 3)
        )
        self.default_words_per_chapter = int(
            self.config.get("default_words_per_chapter", 500)
        )
        self.default_language = self.config.get("default_language", "zh")
        self.default_temperature = float(
            self.config.get("default_temperature", 0.85)
        )

    # ==================== 主入口 ====================

    async def execute(self, **kwargs) -> dict:
        action = kwargs.pop("action", "generate")
        try:
            if action == "generate":
                return self._ok(await self._generate(**kwargs))
            if action == "continue":
                kwargs["continue_from"] = kwargs.get("file") or kwargs.get("continue_from")
                return self._ok(await self._generate(**kwargs))
            if action == "list_languages":
                return self._ok(self._list_languages())
            return self._err(f"未知 action: {action}")
        except Exception as e:
            logger.exception("NovelWriter 执行失败")
            return self._err(str(e))

    # ==================== 语言 ====================

    def _list_languages(self) -> dict:
        return {
            "languages": [
                {"code": code, "name": cfg["name"]}
                for code, cfg in LANG_CONFIG.items()
            ],
            "default": self.default_language,
        }

    def _get_lang_config(self, lang: str) -> dict:
        if lang in LANG_CONFIG:
            return LANG_CONFIG[lang]
        logger.warning(f"不支持的语言: {lang}，使用中文")
        return LANG_CONFIG["zh"]

    # ==================== 输入校验 ====================

    def _validate_inputs(self, **kwargs):
        required = ["genre", "title", "outline", "characters"]
        for p in required:
            if not kwargs.get(p):
                raise ValueError(f"缺少必需参数: {p}")

        cc = int(kwargs.get("chapter_count", self.default_chapter_count))
        wpc = int(kwargs.get("words_per_chapter", self.default_words_per_chapter))
        temp = float(kwargs.get("temperature", self.default_temperature))

        if not (1 <= cc <= 20):
            raise ValueError(f"chapter_count 需在 1-20，当前 {cc}")
        if not (200 <= wpc <= 2000):
            raise ValueError(f"words_per_chapter 需在 200-2000，当前 {wpc}")
        if not (0 <= temp <= 1):
            raise ValueError(f"temperature 需在 0-1，当前 {temp}")

        lang = kwargs.get("language", self.default_language)
        if lang not in LANG_CONFIG:
            logger.warning(f"不支持的语言 {lang}，将使用中文")
        return True

    # ==================== LLM 调用 ====================

    async def _call_llm(
        self,
        prompt: str,
        temperature: float = 0.85,
        max_tokens: int = 2048,
        system: str = "",
    ) -> str:
        """通过 dispatcher.chat 调 LLM（agnes → pollinations 降级）。"""
        from engines import dispatcher

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            text, used = await dispatcher.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            logger.info(f"[llm] 引擎: {used}, 返回 {len(text)} 字")
            return text.strip()
        except Exception as e:
            logger.error(f"[llm] 调用失败: {e}")
            return ""

    # ==================== 加载已有小说 ====================

    def _load_existing_novel(self, filepath: str) -> Optional[dict]:
        path = Path(filepath)
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")

        title_match = re.search(
            r"(?:标题|タイトル|Title|Título|Titre|Titel|Titolo|제목|العنوان|ชื่อเรื่อง|शीर्षक)[：:]\s*(.+?)(?:\n|$)",
            content,
        )
        genre_match = re.search(
            r"(?:类型|ジャンル|Genre|Género|Genre|Genere|장르|النوع|ประเภท|शैली)[：:]\s*(.+?)(?:\n|$)",
            content,
        )
        words_match = re.search(
            r"(?:总字数|総文字数|Total Words|Palabras totales|Mots totaux|Wörter insgesamt|Parole totali|Palavras totais|총 글자수|إجمالي الكلمات|จำนวนคำทั้งหมด|कुल शब्द)[：:]\s*(\d+)",
            content,
        )

        title = title_match.group(1).strip() if title_match else None
        genre = genre_match.group(1).strip() if genre_match else None
        total_words = int(words_match.group(1)) if words_match else 0

        lang_patterns = [
            r"语言[：:]\s*(.+)", r"言語[：:]\s*(.+)", r"Language[：:]\s*(.+)",
            r"Lingua[：:]\s*(.+)", r"Idioma[：:]\s*(.+)", r"Langue[：:]\s*(.+)",
            r"Sprache[：:]\s*(.+)", r"Język[：:]\s*(.+)", r"Språk[：:]\s*(.+)",
            r"Kieli[：:]\s*(.+)", r"Γλώσσα[：:]\s*(.+)", r"שפה[：:]\s*(.+)",
            r"भाषा[：:]\s*(.+)",
        ]
        language = "zh"
        for pat in lang_patterns:
            m = re.search(pat, content)
            if m:
                language = m.group(1).strip()
                break

        # 语言修正
        if language == "zh":
            if "日本語" in content or "あらすじ" in content:
                language = "ja"
            elif "English" in content or "Synopsis" in content:
                language = "en"

        chapters = self._parse_chapters_from_file(filepath)

        return {
            "title": title,
            "genre": genre,
            "language": language,
            "chapters": chapters,
            "chapter_count": len(chapters),
            "total_words": total_words,
            "filepath": str(path),
        }

    def _parse_chapters_from_file(self, filepath: str) -> list[dict]:
        path = Path(filepath)
        if not path.exists():
            return []

        content = path.read_text(encoding="utf-8")

        # 章节分割
        split_pattern = (
            r"\n(?=第\d+章[：:]|Chapter \d+[:：]|Capítulo \d+[:：]|"
            r"Chapitre \d+[:：]|Kapitel \d+[:：]|Capitolo \d+[:：]|"
            r"제\d+장[：:]|الفصل \d+[:：]|บทที่ \d+[:：]|"
            r"Hoofdstuk \d+[:：]|Rozdział \d+[:：]|Luku \d+[:：]|"
            r"Κεφάλαιο \d+[:：]|פרק \d+[:：])"
        )
        parts = re.split(split_pattern, content)

        patterns = [
            (r"第(\d+)章[：:]\s*(.+?)(?:\n|$)", "zh"),
            (r"Chapter (\d+)[：:]\s*(.+?)(?:\n|$)", "en"),
            (r"Capítulo (\d+)[：:]\s*(.+?)(?:\n|$)", "es"),
            (r"Chapitre (\d+)[：:]\s*(.+?)(?:\n|$)", "fr"),
            (r"Kapitel (\d+)[：:]\s*(.+?)(?:\n|$)", "de"),
            (r"Capitolo (\d+)[：:]\s*(.+?)(?:\n|$)", "it"),
            (r"제(\d+)장[：:]\s*(.+?)(?:\n|$)", "ko"),
            (r"الفصل (\d+)[：:]\s*(.+?)(?:\n|$)", "ar"),
            (r"บทที่ (\d+)[：:]\s*(.+?)(?:\n|$)", "th"),
            (r"Hoofdstuk (\d+)[：:]\s*(.+?)(?:\n|$)", "nl"),
            (r"Rozdział (\d+)[：:]\s*(.+?)(?:\n|$)", "pl"),
            (r"Luku (\d+)[：:]\s*(.+?)(?:\n|$)", "fi"),
            (r"Κεφάλαιο (\d+)[：:]\s*(.+?)(?:\n|$)", "el"),
            (r"פרק (\d+)[：:]\s*(.+?)(?:\n|$)", "he"),
        ]

        # 需要移除的各种章节标题行
        title_line_patterns = [
            r"^第\d+章[：:]\s*.+?\n",
            r"^Chapter \d+[：:]\s*.+?\n",
            r"^Capítulo \d+[：:]\s*.+?\n",
            r"^Chapitre \d+[：:]\s*.+?\n",
            r"^Kapitel \d+[：:]\s*.+?\n",
            r"^Capitolo \d+[：:]\s*.+?\n",
            r"^제\d+장[：:]\s*.+?\n",
            r"^الفصل \d+[：:]\s*.+?\n",
            r"^บทที่ \d+[：:]\s*.+?\n",
            r"^Hoofdstuk \d+[：:]\s*.+?\n",
            r"^Rozdział \d+[：:]\s*.+?\n",
            r"^Luku \d+[：:]\s*.+?\n",
            r"^Κεφάλαιο \d+[：:]\s*.+?\n",
            r"^פרק \d+[：:]\s*.+?\n",
        ]

        chapters = []
        for part in parts:
            if not part.strip():
                continue
            for pat, _ in patterns:
                m = re.search(pat, part)
                if not m:
                    continue
                idx = int(m.group(1))
                title_text = m.group(2).strip()
                content_part = part
                for tp in title_line_patterns:
                    content_part = re.sub(tp, "", content_part, flags=re.MULTILINE)
                content_part = re.sub(r"^-{40,}\n", "", content_part, flags=re.MULTILINE)
                content_part = content_part.strip()
                if content_part:
                    chapters.append({
                        "index": idx,
                        "title": title_text,
                        "content": content_part,
                    })
                break
        return chapters

    # ==================== 保存 ====================

    def _save_novel(self, data: dict, is_continue: bool = False) -> str:
        title = data.get("title", "untitled")
        lang = data.get("language", "zh")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        lang_config = self._get_lang_config(lang)
        labels = lang_config.get("labels", {})

        safe_title = re.sub(r'[<>:"/\\|?*]', "", title)
        safe_title = safe_title.replace(" ", "_").strip("_")

        if is_continue and data.get("filepath"):
            filepath = Path(data["filepath"])
        else:
            filepath = self.output_dir / f"{lang}_{safe_title}_{ts}.txt"

        lines = []
        lines.append("=" * 60)
        lines.append(f"  {labels.get('title', '标题')}：{data.get('title', '')}")
        lines.append(f"  {labels.get('genre', '类型')}：{data.get('genre', '')}")
        lines.append(f"  {labels.get('language', '语言')}：{data.get('language', 'zh')}")
        lines.append(f"  {labels.get('model', '模型')}：{data.get('model_used', '')}")
        lines.append(f"  {labels.get('generated_at', '生成时间')}：{data.get('generated_at', '')}")
        lines.append(f"  {labels.get('total_words', '总字数')}：{data.get('total_words', 0)}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"【{labels.get('summary', '小说简介')}】")
        lines.append(data.get("summary", ""))
        lines.append("")
        lines.append("=" * 60)
        lines.append("")

        chapter_label = lang_config.get("chapter_format", "第{chapter}章")
        for ch in data.get("chapters", []):
            lines.append(f"{chapter_label.format(chapter=ch['index'])}：{ch['title']}")
            lines.append("-" * 40)
            lines.append(ch["content"])
            lines.append("")
            lines.append("-" * 40)
            lines.append("")

        filepath.write_text("\n".join(lines), encoding="utf-8")
        return str(filepath)

    # ==================== 单章生成 ====================

    @staticmethod
    def _clean_chapter_title(raw: str) -> str:
        """清理 LLM 生成的章节标题。

        - 去掉引号 / 书名号
        - 去掉 '第X章：' / 'Chapter N:' 等前缀
        - 去掉 Markdown 井号
        """
        s = (raw or "").strip()
        # 去掉首尾引号和 Markdown 标记
        s = s.strip('"').strip("'").strip("「").strip("」").strip("『").strip("』")
        s = re.sub(r"^#+\s*", "", s)

        # 去掉章节前缀（中/英/日/韩/法/德/西/意）
        prefix_pattern = (
            r"^\s*(?:"
            r"第\s*\d+\s*章|"
            r"Chapter\s+\d+|"
            r"Capítulo\s+\d+|"
            r"Chapitre\s+\d+|"
            r"Kapitel\s+\d+|"
            r"Capitolo\s+\d+|"
            r"제\s*\d+\s*장|"
            r"الفصل\s+\d+|"
            r"บทที่\s+\d+"
            r")\s*[：:\-—.]\s*"
        )
        s = re.sub(prefix_pattern, "", s, flags=re.IGNORECASE)

        # 去掉首尾冒号
        s = s.strip("：: ").strip()
        # 单行化（避免标题里带换行）
        s = s.splitlines()[0].strip() if s else ""
        return s

    @staticmethod
    def _clean_chapter_content(raw: str) -> str:
        """清理章节正文。

        - 去掉开头的 Markdown 标题行
        - 去掉纯分隔线行（---/***/===）
        - 去掉重复的章节标题行
        - 压缩过多空行
        """
        if not raw:
            return ""

        lines = raw.splitlines()
        cleaned: list[str] = []
        for line in lines:
            stripped = line.strip()

            # 跳过 Markdown 标题行（# xxx）
            if re.match(r"^#{1,6}\s+", stripped):
                continue

            # 跳过分隔线（--- / *** / === / ___，3 个以上）
            if re.match(r"^[-*=_]{3,}\s*$", stripped):
                continue

            # 跳过形如 "第X章：xxx" 的重复标题行（正文开头常见）
            if re.match(
                r"^第\s*\d+\s*章\s*[：:\-—.]\s*\S+$",
                stripped,
            ):
                continue

            cleaned.append(line)

        # 用正则把连续 3 个以上空行压成 2 个
        text = "\n".join(cleaned)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
        
    async def _generate_chapter(
        self, genre, title, outline, characters,
        chapter_index, total_chapters, style,
        temperature, lang_config, prev_chapters=None,
    ) -> dict:
        system_template = lang_config.get("system_prompt", "你是一位专业的小说作家")
        language_instruction = lang_config.get("language_instruction", "")

        system = system_template.format(genre=genre)
        system += f"\n\n小说标题：{title}\n"
        system += f"小说类型：{genre}\n"
        system += f"故事大纲：{outline}\n"
        system += f"角色设定：{characters}\n"
        system += f"写作风格：{style}\n"
        system += f"当前写第 {chapter_index}/{total_chapters} 章\n\n"
        system += language_instruction

        context = ""
        if prev_chapters:
            recent = prev_chapters[-2:]
            context = "\n\n前面章节内容：\n"
            for c in recent:
                context += f"第{c['index']}章：{c['title']}\n"
                context += c["content"][:300] + "...\n\n"

        # ---------- 章节标题 ----------
        title_prompt = (
            f"{context}\n\n请为第{chapter_index}章生成一个吸引人的章节标题。"
            f"要求：只输出标题本身，不要带'第X章：'前缀，不要引号，不要其他说明文字。"
        )
        chapter_title = await self._call_llm(
            title_prompt, temperature, max_tokens=100, system=system,
        )
        chapter_title = self._clean_chapter_title(chapter_title)
        if not chapter_title:
            chapter_title = f"第{chapter_index}章"

        # ---------- 章节内容 ----------
        content_prompt = f"""{context}

章节标题：{chapter_title}

请以场景为单位写出本章内容。每个场景应包含两部分：
1. 场景描述：描述画面、环境、动作（用于生成视频）。
2. 旁白/对话：角色说的话或叙述（用于语音）。

每个场景的旁白字数控制在 30-50 字（中文），场景描述不超过 30 字。
请用 '【场景】' 标记每个场景的开始，场景内先写场景描述（以 '画面：' 开头），再写旁白（以 '旁白：' 开头）。

格式要求（重要）：
- 不要使用 Markdown 标题（#、##、###）
- 不要使用分隔线（---、***、===）
- 不要重复章节标题
- 直接从第一个 '【场景】' 开始写正文

请写出第{chapter_index}章的完整内容："""

        content = await self._call_llm(
            content_prompt, temperature, max_tokens=2048, system=system,
        )
        content = self._clean_chapter_content(content)

        return {
            "index": chapter_index,
            "title": chapter_title,
            "content": content,
        }
        
    # ==================== 简介 ====================

    async def _generate_summary(
        self, genre, title, outline, characters, chapters, lang_config,
    ) -> str:
        if not chapters:
            return f"《{title}》是一部{genre}小说，讲述了{outline}的故事。"

        chapter_summaries = "\n".join(
            [f"第{c['index']}章：{c['title']}" for c in chapters]
        )

        # 找语言代码
        lang_code = "zh"
        for code, cfg in LANG_CONFIG.items():
            if cfg.get("name") == lang_config.get("name"):
                lang_code = code
                break

        prompt_templates = {
            "zh": f"你是一位小说编辑，请为以下小说撰写一段吸引人的简介（200字以内）：\n\n小说标题：{title}\n小说类型：{genre}\n故事大纲：{outline}\n角色设定：{characters}\n章节概览：{chapter_summaries}\n\n请写出小说简介：",
            "en": f"You are a novel editor. Write an engaging synopsis (within 200 words):\n\nTitle: {title}\nGenre: {genre}\nOutline: {outline}\nCharacters: {characters}\nChapters: {chapter_summaries}\n\nSynopsis:",
            "ja": f"あなたは小説編集者です。以下の小説の魅力的なあらすじを書いてください（200字以内）：\n\nタイトル：{title}\nジャンル：{genre}\nあらすじ：{outline}\nキャラクター：{characters}\n章の概要：{chapter_summaries}\n\nあらすじ：",
        }
        prompt = prompt_templates.get(lang_code, prompt_templates["zh"])

        summary = await self._call_llm(prompt, 0.7, max_tokens=512)
        if not summary:
            summary = f"《{title}》是一部{genre}小说，讲述了{outline}的故事。"
        return summary

    # ==================== 主流程 ====================

    async def _generate(self, **kwargs) -> dict:
        start = time.time()
        self._validate_inputs(**kwargs)

        genre = kwargs["genre"]
        title = kwargs["title"]
        outline = kwargs["outline"]
        characters = kwargs["characters"]
        chapter_count = int(kwargs.get("chapter_count", self.default_chapter_count))
        words_per_chapter = int(kwargs.get("words_per_chapter", self.default_words_per_chapter))
        style = kwargs.get("style", "细腻")
        temperature = float(kwargs.get("temperature", self.default_temperature))
        continue_from = kwargs.get("continue_from")
        language = kwargs.get("language", self.default_language)

        lang_config = self._get_lang_config(language)

        existing_data = None
        existing_chapters = []
        start_index = 1
        chapters_to_generate = chapter_count
        target_total = chapter_count

        if continue_from:
            existing_data = self._load_existing_novel(continue_from)
            if existing_data:
                existing_chapter_count = existing_data.get("chapter_count", 0)
                existing_chapters = existing_data.get("chapters", [])
                genre = existing_data.get("genre", genre)
                title = existing_data.get("title", title)
                language = existing_data.get("language", language)
                lang_config = self._get_lang_config(language)
                start_index = existing_chapter_count + 1
                target_total = existing_chapter_count + chapter_count

        logger.info(
            f"生成小说: {title} 语言={language} 类型={genre} "
            f"已有={len(existing_chapters)} 需生成={chapters_to_generate}"
        )

        all_chapters = list(existing_chapters)
        prev_chapters = list(existing_chapters)

        for i in range(chapters_to_generate):
            chapter_idx = start_index + i
            logger.info(f"  第 {chapter_idx}/{target_total} 章")
            chapter = await self._generate_chapter(
                genre, title, outline, characters,
                chapter_idx, target_total, style,
                temperature, lang_config, prev_chapters,
            )
            all_chapters.append(chapter)
            prev_chapters.append(chapter)
            await asyncio.sleep(0.3)

        logger.info("  生成简介...")
        summary = await self._generate_summary(
            genre, title, outline, characters, all_chapters, lang_config,
        )

        total_words = sum(len(c["content"]) for c in all_chapters)

        result = {
            "title": title,
            "genre": genre,
            "language": language,
            "summary": summary,
            "chapters": all_chapters,
            "chapter_count": len(all_chapters),
            "total_words": total_words,
            "model_used": "dispatcher.chat",
            "generated_at": datetime.now().isoformat(),
            "generation_time": f"{time.time() - start:.2f}s",
        }

        if existing_data and existing_data.get("filepath"):
            result["filepath"] = existing_data["filepath"]

        saved_path = self._save_novel(result, is_continue=bool(existing_data))
        result["saved_to"] = saved_path
        result["file_url"] = f"/files/novel/{Path(saved_path).name}"

        logger.info(f"完成: {len(all_chapters)} 章 {total_words} 字")

        return result

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