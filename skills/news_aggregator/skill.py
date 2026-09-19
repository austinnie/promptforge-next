# skills/news_aggregator/skill.py
"""新闻聚合 skill。

能力：
    fetch        抓取 RSS 新闻（可按分类），可选生成 AI 摘要
    list_feeds   列出所有分类和 RSS 源

改造点：
    - Ollama → dispatcher.chat
    - execute → async
    - 输出目录 → data/assets/news/
    - AI 摘要默认关闭（可选参数开启），避免超 token
"""

import asyncio
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

from .feeds import CATEGORY_NAMES, DEFAULT_FEEDS


class NewsAggregator:
    """新闻聚合器。"""

    NAME = "news_aggregator"
    VERSION = "2.0.0"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

        self.output_dir = Path(
            self.config.get("output_dir", "./data/assets/news")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 缓存目录（不入 /files/）
        self.cache_dir = Path(
            self.config.get("cache_dir", "./data/cache/news")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.feed_timeout = int(self.config.get("feed_timeout", 10))
        self.max_workers = int(self.config.get("max_workers", 10))
        self.top_n = int(self.config.get("top_n", 50))
        self.dedup_key_length = int(self.config.get("dedup_key_length", 30))
        self.cache_ttl = int(self.config.get("cache_ttl", 1800))

        # AI 摘要
        self.ai_temperature = float(self.config.get("ai_temperature", 0.3))
        self.ai_max_articles = int(self.config.get("ai_summary_max_articles", 20))

    # ==================== 主入口 ====================

    async def execute(self, **kwargs) -> dict:
        action = kwargs.pop("action", "fetch")
        try:
            if action == "list_feeds":
                return self._ok(self._list_feeds())
            if action == "fetch":
                return self._ok(await self._fetch(**kwargs))
            return self._err(f"未知 action: {action}")
        except Exception as e:
            logger.exception("NewsAggregator 执行失败")
            return self._err(str(e))

    def _list_feeds(self) -> dict:
        return {
            "categories": [
                {
                    "id": k,
                    "name": CATEGORY_NAMES.get(k, k),
                    "feed_count": len(v),
                    "feeds": v,
                }
                for k, v in DEFAULT_FEEDS.items()
            ]
        }

    async def _fetch(
        self,
        category: str = "",
        sources: str = "",
        top_n: Optional[int] = None,
        validate: bool = True,
        with_summary: bool = False,
    ) -> dict:
        start = time.time()

        if not FEEDPARSER_AVAILABLE:
            raise RuntimeError("feedparser 未安装，请 pip install feedparser")

        feeds = self._load_feeds(category or None, sources or None, validate)
        if not feeds:
            raise RuntimeError("未找到可用的 RSS 源")

        logger.info(f"开始抓取 {len(feeds)} 个源...")
        all_items = await asyncio.to_thread(self._fetch_all_feeds, feeds)
        if not all_items:
            raise RuntimeError("未抓取到任何新闻")

        logger.info(f"抓到 {len(all_items)} 条，去重中...")
        unique = self._deduplicate(all_items)
        logger.info(f"去重后 {len(unique)} 条")

        display_n = top_n if top_n is not None else self.top_n
        display_n = min(display_n, len(unique))
        top_items = unique[:display_n]

        # AI 摘要（可选）
        summary_text = ""
        summary_engine = ""
        if with_summary:
            logger.info("生成 AI 摘要...")
            summary_text, summary_engine = await self._generate_ai_summary(top_items)

        # 报告
        report = self._generate_report(unique, category or None, summary_text)
        report_path = self._save_report(report, category or None)

        result = {
            "total_fetched": len(all_items),
            "unique_count": len(unique),
            "display_count": len(top_items),
            "feeds_count": len(feeds),
            "category": category or "all",
            "category_name": CATEGORY_NAMES.get(category, category) if category else "全部",
            "articles": top_items,
            "summary": summary_text,
            "summary_engine": summary_engine,
            "report_file": self._to_url(str(report_path)) if report_path else "",
            "generated_at": datetime.now().isoformat(),
            "elapsed": f"{time.time() - start:.1f}s",
        }
        logger.info(f"完成: {len(unique)} 条，耗时 {result['elapsed']}")
        return result

    # ==================== RSS 源加载 ====================

    def _load_feeds(
        self, category: Optional[str], sources: Optional[str], validate: bool,
    ) -> list[str]:
        feeds: list[str] = []

        if category:
            if category not in DEFAULT_FEEDS:
                logger.warning(f"未知分类: {category}")
                return []
            feeds = list(DEFAULT_FEEDS[category])

        if sources:
            src_list = [s.strip().lower() for s in sources.split(",") if s.strip()]
            for cat_feeds in DEFAULT_FEEDS.values():
                for f in cat_feeds:
                    if any(s in f.lower() for s in src_list):
                        feeds.append(f)

        if not feeds:
            for cat_feeds in DEFAULT_FEEDS.values():
                feeds.extend(cat_feeds)

        feeds = list(set(feeds))

        if validate:
            cached = self._get_cached_feeds(category or "all")
            if cached:
                logger.info(f"使用缓存: {len(cached)} 个源")
                return cached
            feeds = self._validate_feeds(feeds)
            self._save_cache(category or "all", feeds)

        logger.info(f"最终加载 {len(feeds)} 个源")
        return feeds

    def _validate_feeds(self, feeds: list[str]) -> list[str]:
        if not feeds:
            return []

        logger.info(f"验证 {len(feeds)} 个 RSS 源...")
        valid: list[str] = []

        def check(url: str) -> Optional[str]:
            try:
                feed = feedparser.parse(url)
                return url if feed.entries else None
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futures = {ex.submit(check, u): u for u in feeds}
            for fut in as_completed(futures):
                r = fut.result()
                if r:
                    valid.append(r)

        logger.info(f"验证完成: {len(valid)}/{len(feeds)}")
        return valid

    def _cache_file(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _get_cached_feeds(self, key: str) -> Optional[list[str]]:
        p = self._cache_file(key)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if time.time() - data.get("timestamp", 0) < self.cache_ttl:
                return data.get("feeds", [])
        except Exception:
            pass
        return None

    def _save_cache(self, key: str, feeds: list[str]) -> None:
        try:
            self._cache_file(key).write_text(
                json.dumps({"timestamp": time.time(), "feeds": feeds},
                           ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    # ==================== 抓取 ====================

    def _fetch_all_feeds(self, feeds: list[str]) -> list[dict]:
        all_items: list[dict] = []
        for url in feeds:
            all_items.extend(self._fetch_one(url))
        return all_items

    def _fetch_one(self, url: str) -> list[dict]:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get("title", url.split("/")[2] if "//" in url else "未知")
            items = []
            for entry in feed.entries:
                summary = entry.get("summary", "") or ""
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                items.append({
                    "title": entry.get("title", "无标题"),
                    "link": entry.get("link", ""),
                    "summary": summary or "无摘要",
                    "published": entry.get("published") or entry.get("updated", ""),
                    "author": entry.get("author", "未知"),
                    "source": source_name,
                    "feed_url": url,
                })
            return items
        except Exception as e:
            logger.warning(f"抓取失败 {url[:60]}: {e}")
            return []

    def _deduplicate(self, items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique: list[dict] = []
        for it in items:
            key = it.get("title", "")[: self.dedup_key_length].lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(it)
        return unique

    # ==================== AI 摘要 ====================

    async def _generate_ai_summary(
        self, articles: list[dict],
    ) -> tuple[str, str]:
        if not articles:
            return "暂无新闻", ""

        lines = []
        for i, art in enumerate(articles[: self.ai_max_articles], 1):
            s = art.get("summary", "")[:100]
            lines.append(f"{i}. {art['title']}\n   {s}\n   来源: {art['source']}\n")
        news_text = "\n".join(lines)

        prompt = (
            f"请根据以下新闻内容，生成一份每日新闻简报摘要。\n\n"
            f"要求：\n"
            f"1. 按主题/类别整理\n"
            f"2. 列出最重要的新闻\n"
            f"3. 每条新闻用一句话概括核心内容\n"
            f"4. 格式简洁清晰，用中文\n\n"
            f"新闻列表：\n{news_text}\n\n"
            f"请生成简报摘要："
        )

        try:
            from engines import dispatcher
            text, used = await dispatcher.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=self.ai_temperature,
                max_tokens=1024,
            )
            return text.strip(), used
        except Exception as e:
            logger.warning(f"AI 摘要失败: {e}")
            return f"（AI 摘要生成失败: {e}）", ""

    # ==================== 报告 ====================

    def _generate_report(
        self, articles: list[dict], category: Optional[str], summary_text: str,
    ) -> str:
        sep = "=" * 60
        lines = [
            sep,
            "   📰 每日新闻简报",
            sep,
            f"   生成时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
        ]
        if category:
            lines.append(f"   分类: {CATEGORY_NAMES.get(category, category)}")
        lines.append(f"   新闻数: {len(articles)} 条")
        lines.append(sep)
        lines.append("")

        if summary_text:
            lines.append("【AI 智能摘要】")
            lines.append("-" * 40)
            lines.append(summary_text)
            lines.append("")
            lines.append("-" * 60)
            lines.append("")

        for i, art in enumerate(articles, 1):
            lines.append(f"【{i}】{art.get('title', '无标题')}")
            if art.get("published"):
                lines.append(f"  时间: {art['published']}")
            lines.append(f"  来源: {art.get('source', '未知')}")
            if art.get("summary"):
                lines.append(f"  摘要: {art['summary']}")
            if art.get("link"):
                lines.append(f"  链接: {art['link']}")
            lines.append("")

        lines.append(sep)
        lines.append("   简报结束")
        lines.append(sep)
        return "\n".join(lines)

    def _save_report(self, content: str, category: Optional[str]) -> Optional[Path]:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        cat = category or "all"
        path = self.output_dir / f"news_{cat}_{ts}.txt"
        path.write_text(content, encoding="utf-8")
        return path

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