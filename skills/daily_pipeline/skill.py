# skills/daily_pipeline/skill.py
"""daily_pipeline - 每日自动化任务编排。

一键完成：生成图片 → AI 鉴赏写文章 → 追加二维码 → 微信排版 → 推送草稿箱

改造点：
    - 生图走 engines.dispatcher（不依赖已删的 image_generator skill）
    - 调 image_curator / wechat_formatter 走新版 async execute
    - execute 改 async
    - 输出目录 → data/assets/daily/
"""

import asyncio
import logging
import random
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

from .topics import (
    ALL_TOPICS,
    PRESET_CAT_TO_STYLES,
    STYLE_KEYWORDS,
    STYLE_TO_PRESET_CATS,
    TOPICS_BY_STYLE,
    VALID_PRESET_CATEGORIES,
    VARIANT_TEMPLATES,
)


class DailyPipeline:
    """每日自动化任务（生成 → 鉴赏 → 排版 → 发布）。"""

    NAME = "daily_pipeline"
    VERSION = "2.0.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        defaults = {
            "output_root": "./data/assets/daily",
            "qr": "./data/assets/qr/公众号结束处.png",
            "theme": "newspaper",
            "count": 6,
            "topics_file": "./data/topics.txt",
            "auto_publish": False,   # 默认不推送（微信凭证未必配好）
            "image_size": 1024,
        }
        for k, v in defaults.items():
            self.config.setdefault(k, v)

        self.output_root = Path(self.config["output_root"])
        self.output_root.mkdir(parents=True, exist_ok=True)

    # ==================== 主入口 ====================

    async def execute(self, **kwargs) -> dict:
        action = kwargs.pop("action", "run")
        try:
            if action == "run":
                return self._ok(await self._run(**kwargs))
            if action == "list_presets":
                return self._ok(self.list_presets())
            if action == "list_topics":
                return self._ok(self.list_topics())
            return self._err(f"未知 action: {action}")
        except Exception as e:
            logger.exception("DailyPipeline 执行失败")
            return self._err(str(e))

    async def _run(self, **kwargs) -> dict:
        start = time.time()

        topic = kwargs.get("topic") or None
        preset = kwargs.get("preset") or None
        preset_category = kwargs.get("preset_category") or None
        vary_preset = bool(kwargs.get("vary_preset", False))
        count = int(kwargs.get("count", self.config["count"]))
        theme = kwargs.get("theme", self.config["theme"])
        qr = kwargs.get("qr", self.config["qr"])
        publish = kwargs.get("publish", self.config["auto_publish"])
        skip_curate = bool(kwargs.get("skip_curate", False))
        skip_generate = bool(kwargs.get("skip_generate", False))
        image_dir_arg = kwargs.get("image_dir")

        # 1. 选主题 + 预设
        topic, preset = self.pick_topic_and_preset(
            topic=topic, preset=preset, preset_category=preset_category,
        )
        logger.info(f"🎯 主题: {topic}")
        logger.info(f"🎨 预设: {preset or '（无）'}")

        today_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_str = datetime.now().strftime("%Y-%m-%d")

        # 2. 确定图片目录
        if skip_generate:
            if not image_dir_arg:
                raise ValueError("skip_generate=True 必须提供 image_dir")
            image_dir = Path(image_dir_arg).resolve()
            if not image_dir.exists():
                raise FileNotFoundError(f"图片目录不存在: {image_dir}")
        else:
            image_dir = (self.output_root / f"{today_ts}_images").resolve()
            image_dir.mkdir(parents=True, exist_ok=True)

        result = {
            "topic": topic,
            "preset": preset,
            "image_dir": str(image_dir),
            "image_count": 0,
            "article_dir": "",
            "md_path": "",
            "preview_path": "",
            "clipboard_path": "",
            "published": False,
            "publish_error": None,
        }

        # 3. 步骤 1：生图
        if not skip_generate:
            paths = await self.generate_images(
                topic, count, image_dir, preset, vary_preset,
            )
            if not paths:
                raise RuntimeError("未生成任何图片")
            result["image_count"] = len(paths)
            logger.info(f"✅ 生成 {len(paths)} 张 → {image_dir}")

        if skip_curate:
            result["elapsed"] = f"{time.time() - start:.1f}s"
            return result

        # 4. 步骤 2：鉴赏 + 文章（用新 image_curator）
        title = f"{topic}·{date_str}"
        md_path = await self.curate_article(image_dir, title)
        if not md_path:
            raise RuntimeError("鉴赏/文章生成失败")
        result["md_path"] = str(md_path)

        # 5. 步骤 3：排版（用新 wechat_formatter）
        qr_path = Path(qr).resolve()
        if not qr_path.exists():
            logger.warning(f"⚠️ 二维码不存在，跳过: {qr_path}")
            qr_path = None

        article_dir = await self.format_wechat(md_path, theme, qr_path)
        if not article_dir:
            raise RuntimeError("排版失败")
        result["article_dir"] = str(article_dir)
        result["preview_path"] = self._path_to_url(article_dir / "preview.html")
        result["clipboard_path"] = self._path_to_url(article_dir / "clipboard.html")

        # 6. 步骤 4：推送
        if publish:
            pub = await self.publish_wechat(article_dir)
            result["published"] = pub.get("published", False)
            result["publish_error"] = pub.get("error")
        else:
            result["published"] = False
            result["publish_error"] = "未启用推送"

        result["elapsed"] = f"{time.time() - start:.1f}s"
        logger.info(f"🎉 完成，耗时 {result['elapsed']}")
        return result

    # ==================== 步骤 1：生图 ====================

    async def generate_images(
        self,
        topic: str,
        count: int,
        out_dir: Path,
        preset: Optional[str],
        vary_preset: bool = False,
    ) -> List[Path]:
        """用 dispatcher 生成图片，保存到 out_dir。"""
        from engines import dispatcher

        out_dir = out_dir.resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        # 预设构造器
        prompt_builder = None
        if preset:
            try:
                from packages.forge_core.preset_bridge import get_default_bridge
                bridge = get_default_bridge()
                if bridge.is_ready():
                    prompt_builder = bridge
                    logger.info(f"🎯 使用预设: {preset}")
            except Exception as e:
                logger.warning(f"⚠️ 预设加载失败: {e}")

        # vary_preset: 收集同分类预设
        preset_pool: List[str] = []
        if vary_preset and preset:
            try:
                from packages.forge_core.presets_meta import PRESET_META
                meta = PRESET_META.get(preset)
                if meta and len(meta) >= 2:
                    cat = meta[1]
                    preset_pool = [
                        n for n, m in PRESET_META.items()
                        if isinstance(m, (list, tuple)) and len(m) >= 2
                        and m[1] == cat and n != preset
                    ]
                    logger.info(f"🎲 vary_preset: {len(preset_pool)} 个同分类预设")
            except Exception:
                pass

        variants = VARIANT_TEMPLATES.copy()
        random.shuffle(variants)

        size = int(self.config["image_size"])
        raw_paths: List[Path] = []

        for i in range(count):
            variant_tpl = variants[i % len(variants)]
            varied_subject = variant_tpl.format(topic=topic)

            current_preset = preset
            if preset_pool and i > 0:
                current_preset = random.choice(preset_pool)

            if prompt_builder:
                prompt, _ = prompt_builder.build_prompt(
                    preset=current_preset,
                    mode="random",
                    subject_override=varied_subject,
                    max_tokens=77,
                    return_detail=True,
                )
            else:
                prompt = (
                    f"{varied_subject}, masterpiece, best quality, 8k, "
                    f"highly detailed, cinematic lighting, professional photography"
                )

            logger.info(f"🎨 [{i + 1}/{count}] {variant_tpl[:55]}...")
            try:
                img, used = await dispatcher.generate_image(
                    prompt=prompt, width=size, height=size,
                )
            except Exception as e:
                logger.warning(f"生成失败: {e}")
                continue

            # 存到 out_dir，用临时名，最后统一改名
            tmp_path = out_dir / f"_tmp_{i:02d}.png"
            img.save(tmp_path, "PNG")
            raw_paths.append(tmp_path)

        # 统一重命名：作品01.png 作品02.png ...
        renamed: List[Path] = []
        for i, p in enumerate(raw_paths, 1):
            new_path = out_dir / f"作品{i:02d}.png"
            try:
                if new_path.exists():
                    new_path.unlink()
                p.rename(new_path)
                renamed.append(new_path)
            except Exception as e:
                logger.warning(f"重命名失败: {e}")
                renamed.append(p)

        return renamed

    # ==================== 步骤 2：鉴赏 ====================

    async def curate_article(self, image_dir: Path, title: str) -> Optional[Path]:
        """调 image_curator 生成图文文章，返回 Markdown 路径。"""
        from skills.image_curator import ImageCurator

        curator = ImageCurator()
        logger.info(f"🔍 鉴赏 {image_dir} ...")

        r = await curator.execute(
            action="curate",
            directory=str(image_dir),
            title=title,
            with_intro=True,
        )

        if r.get("status") != "success":
            logger.error(f"鉴赏失败: {r.get('error')}")
            return None

        res = r["result"]
        article_dir = Path(res["article_dir"])
        md_path = article_dir / "article.md"
        logger.info(f"✅ 文章: {md_path}")
        return md_path

    # ==================== 步骤 3：排版 ====================

    async def format_wechat(
        self, md_path: Path, theme: str, qr_path: Optional[Path],
    ) -> Optional[Path]:
        """调 wechat_formatter 排版，返回 article_dir。"""
        import shutil

        from skills.wechat_formatter import WechatFormatter

        # 把 article.md 重命名成 {title}.md，让排版目录更好认
        try:
            article_dir = md_path.parent
            title_hint = article_dir.name  # 如 "20260920_094722_月下松林 2026-09-20"
            # 取最后一段（去掉时间戳）
            if "_" in title_hint:
                title_hint = title_hint.split("_", 2)[-1]
            safe = title_hint.replace(" ", "").replace("/", "").strip() or "article"
            renamed_md = md_path.parent / f"{safe}.md"
            if not renamed_md.exists() and md_path != renamed_md:
                shutil.copy2(md_path, renamed_md)
            use_md = renamed_md if renamed_md.exists() else md_path
        except Exception:
            use_md = md_path

        fmt = WechatFormatter()
        kwargs = {
            "input": str(use_md),
            "theme": theme,
        }
        if qr_path and qr_path.exists():
            kwargs["footer_image"] = str(qr_path)
            kwargs["footer_alt"] = "关注公众号"

        r = await fmt.execute(action="format", **kwargs)
        if r.get("status") != "success":
            logger.error(f"排版失败: {r.get('error')}")
            return None

        res = r["result"]
        out_dir = Path(res["article_dir"])
        logger.info(f"✅ 排版输出: {out_dir}")
        return out_dir

    # ==================== 步骤 4：推送 ====================

    async def publish_wechat(self, article_dir: Path) -> dict:
        from skills.wechat_formatter import WechatFormatter

        fmt = WechatFormatter()
        try:
            r = await fmt.execute(
                action="publish",
                article_dir=str(article_dir),
            )
        except Exception as e:
            logger.error(f"❌ 推送异常: {e}")
            return {"published": False, "error": str(e)}

        if r.get("status") == "success":
            logger.info("✅ 已推送到公众号草稿箱")
            return {"published": True, "error": None}

        err = r.get("error") or "未知错误"
        logger.error(f"❌ 推送失败: {err}")
        logger.info("   排查：1) WECHAT_APP_ID/SECRET  2) IP 白名单  3) 账号是否认证")
        return {"published": False, "error": err}

    # ==================== 主题 / 预设匹配 ====================

    def load_presets_by_category(self) -> Dict[str, List[str]]:
        """从 forge_core.presets_meta 读取，按分类聚合。"""
        try:
            from packages.forge_core.presets_meta import PRESET_META, CATEGORY_ORDER
        except Exception as e:
            logger.warning(f"⚠️ 无法加载 presets_meta: {e}")
            return {}

        groups: Dict[str, List[str]] = {}
        for name, meta in PRESET_META.items():
            if not isinstance(meta, (list, tuple)) or len(meta) < 2:
                continue
            groups.setdefault(meta[1], []).append(name)

        ordered: Dict[str, List[str]] = {}
        for cat in CATEGORY_ORDER:
            if cat in groups:
                ordered[cat] = sorted(groups[cat])
        for cat, lst in groups.items():
            if cat not in ordered:
                ordered[cat] = sorted(lst)
        return ordered

    def list_presets(self) -> dict:
        return self.load_presets_by_category()

    def list_topics(self) -> dict:
        return TOPICS_BY_STYLE

    def load_custom_topics(self) -> List[str]:
        tf = Path(self.config["topics_file"])
        if not tf.exists():
            return []
        try:
            lines = tf.read_text(encoding="utf-8").splitlines()
            return [l.strip() for l in lines
                    if l.strip() and not l.strip().startswith("#")]
        except Exception as e:
            logger.warning(f"⚠️ 读取 topics.txt 失败: {e}")
            return []

    def pick_topic_and_preset(
        self,
        topic: Optional[str],
        preset: Optional[str],
        preset_category: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        presets_by_cat = self.load_presets_by_category()

        if topic and preset:
            return topic, preset

        if topic and not preset:
            style = self._guess_style(topic)
            cats = STYLE_TO_PRESET_CATS.get(style, [])
            return topic, self._pick_preset(presets_by_cat, cats)

        if preset and not topic:
            cat = self._guess_preset_cat(preset)
            styles = PRESET_CAT_TO_STYLES.get(cat or "", []) or list(TOPICS_BY_STYLE.keys())
            return self._pick_topic(styles), preset

        if preset_category:
            chosen = self._pick_preset(presets_by_cat, [preset_category])
            styles = PRESET_CAT_TO_STYLES.get(preset_category, []) or list(TOPICS_BY_STYLE.keys())
            return self._pick_topic(styles), chosen

        all_cats = [c for c in presets_by_cat.keys() if c in PRESET_CAT_TO_STYLES]
        if not all_cats:
            return self._pick_topic(list(TOPICS_BY_STYLE.keys())), None

        cat = random.choice(all_cats)
        return (
            self._pick_topic(PRESET_CAT_TO_STYLES[cat]),
            self._pick_preset(presets_by_cat, [cat]),
        )

    # ==================== 内部工具 ====================

    def _pick_topic(self, styles: List[str]) -> str:
        pool: List[str] = []
        for s in styles:
            pool.extend(TOPICS_BY_STYLE.get(s, []))
        if not pool:
            pool = ALL_TOPICS
        custom = self.load_custom_topics()
        if custom:
            pool = pool + custom * 3
        return random.choice(pool)

    def _pick_preset(
        self, presets_by_cat: Dict[str, List[str]], categories: List[str],
    ) -> Optional[str]:
        pool: List[str] = []
        for c in categories:
            pool.extend(presets_by_cat.get(c, []))
        return random.choice(pool) if pool else None

    def _guess_style(self, topic: str) -> str:
        t = topic.lower()
        best, best_score = None, 0
        for style, kws in STYLE_KEYWORDS.items():
            score = sum(1 for k in kws if k in t)
            if score > best_score:
                best_score, best = score, style
        return best or random.choice(list(TOPICS_BY_STYLE.keys()))

    def _guess_preset_cat(self, preset: str) -> Optional[str]:
        try:
            from packages.forge_core.presets_meta import PRESET_META
            meta = PRESET_META.get(preset)
            if meta and len(meta) >= 2:
                return meta[1]
        except Exception:
            pass

        n = preset.lower()
        if any(k in n for k in ["mecha", "gundam", "eva", "transformers", "rider", "gits"]):
            return "机甲"
        if any(k in n for k in ["chinese", "ink", "cn_", "calligraphy", "hermit", "countryside"]):
            return "国风"
        if "anime" in n or "figure" in n:
            return "动漫"
        if "sketch" in n or "pencil" in n:
            return "素描"
        if any(k in n for k in ["jewelry", "watch", "bag", "nuclear"]):
            return "设计"
        if any(k in n for k in ["landscape", "healing"]):
            return "风景"
        if any(k in n for k in ["cat", "dog", "tiger", "dragon", "horse", "bird",
                                 "crane", "koi", "rabbit", "rat", "ox", "goat",
                                 "monkey", "rooster", "pig", "snake", "flower"]):
            return "动物"
        if any(k in n for k in ["portrait", "daily", "jp_", "pure_serene",
                                 "work_avatar", "beach", "nature_outdoor",
                                 "casual", "farm", "medical", "gallery"]):
            return "人像"
        return None

    @staticmethod
    def _path_to_url(local_path) -> str:
        p = Path(local_path).resolve()
        root = Path("./data/assets").resolve()
        try:
            return f"/files/{p.relative_to(root).as_posix()}"
        except ValueError:
            return str(local_path)

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