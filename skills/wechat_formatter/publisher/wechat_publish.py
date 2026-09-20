# skills/wechat_formatter/publisher/wechat_publish.py
"""微信公众号草稿箱推送。

需要环境变量：
    WECHAT_APP_ID
    WECHAT_APP_SECRET
    WECHAT_AUTHOR（可选）

注意：未认证的个人订阅号无草稿箱 API 权限（errcode=48001）。
"""

import html as html_module
import json
import logging
import os
import re
import tempfile
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


class WechatPublisher:
    """推送文章到微信公众号草稿箱。"""

    def __init__(self):
        self.app_id = os.getenv("WECHAT_APP_ID", "")
        self.app_secret = os.getenv("WECHAT_APP_SECRET", "")
        self.author = os.getenv("WECHAT_AUTHOR", "")
        self._token = None

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    # ==================== token ====================

    def _get_token(self) -> str:
        if self._token:
            return self._token
        if not self.is_configured():
            raise RuntimeError("未配置 WECHAT_APP_ID / WECHAT_APP_SECRET")

        url = (
            "https://api.weixin.qq.com/cgi-bin/token"
            f"?grant_type=client_credential&appid={self.app_id}&secret={self.app_secret}"
        )
        data = requests.get(url, timeout=15).json()
        if "access_token" not in data:
            raise RuntimeError(f"获取 token 失败: {data}")
        self._token = data["access_token"]
        return self._token

    # ==================== 上传 ====================

    def _upload_thumb(self, image_path: str) -> str:
        """上传封面图到永久素材库，返回 media_id。"""
        token = self._get_token()
        url = (
            "https://api.weixin.qq.com/cgi-bin/material/add_material"
            f"?access_token={token}&type=image"
        )
        ext = Path(image_path).suffix.lower()
        ct = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".png": "image/png", ".gif": "image/gif"}.get(ext, "image/jpeg")
        with open(image_path, "rb") as f:
            files = {"media": (Path(image_path).name, f, ct)}
            data = requests.post(url, files=files, timeout=30).json()
        if "media_id" not in data:
            raise RuntimeError(f"上传封面失败: {data}")
        return data["media_id"]

    def _upload_content_image(self, image_path: str, max_retries: int = 3) -> str:
        """上传正文图片，返回微信 CDN URL。"""
        import time
        token = self._get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
        ext = Path(image_path).suffix.lower()
        ct = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".png": "image/png", ".gif": "image/gif"}.get(ext, "image/jpeg")

        for attempt in range(1, max_retries + 1):
            try:
                with open(image_path, "rb") as f:
                    files = {"media": (Path(image_path).name, f, ct)}
                    data = requests.post(url, files=files, timeout=30).json()
                if "url" in data:
                    return data["url"]
            except Exception as e:
                logger.warning(f"上传异常({attempt}): {e}")
            if attempt < max_retries:
                time.sleep(2 * attempt)
        raise RuntimeError(f"上传失败: {image_path}")

    def _download_external(self, url: str) -> str:
        """下载外链图片到临时文件。"""
        url = html_module.unescape(url)
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        ext = ".png" if "png" in ct else ".gif" if "gif" in ct else ".jpg"
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.write(r.content)
        tmp.close()
        return tmp.name

    def _replace_images(self, html: str, article_dir: Path) -> str:
        """把 HTML 里所有图片上传到微信 CDN。"""
        image_dir = article_dir / "images"

        def replace(match):
            src = match.group(1)
            if "mmbiz.qpic.cn" in src:
                return match.group(0)

            local_path = None
            tmp_file = None
            try:
                if src.startswith(("http://", "https://")):
                    tmp_file = self._download_external(src)
                    local_path = tmp_file
                else:
                    p = article_dir / src
                    if not p.exists() and image_dir.exists():
                        p = image_dir / os.path.basename(src)
                    if p.exists():
                        local_path = str(p)

                if local_path:
                    cdn = self._upload_content_image(local_path)
                    return f'src="{cdn}"'
            except Exception as e:
                logger.warning(f"图片上传失败 {src[:50]}: {e}")
            finally:
                if tmp_file and os.path.exists(tmp_file):
                    os.unlink(tmp_file)
            return match.group(0)

        return re.sub(r'src="([^"]+)"', replace, html)

    # ==================== 推送 ====================

    def publish(
        self,
        article_dir: str,
        cover_path: str = "",
        title: str = "",
    ) -> dict:
        """推送文章到草稿箱。

        返回 {"media_id": "...", "preview_url": "..."}
        """
        article_dir = Path(article_dir)
        article_html = article_dir / "article.html"
        if not article_html.exists():
            raise FileNotFoundError(f"缺少 {article_html}")

        html = article_html.read_text(encoding="utf-8")

        # 标题
        if not title:
            m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else article_dir.name

        # 封面
        if not cover_path:
            imgs = sorted((article_dir / "images").glob("*"))
            if imgs:
                cover_path = str(imgs[0])
        if not cover_path or not Path(cover_path).exists():
            raise RuntimeError("微信要求必须有封面图，请用 cover_path 指定")

        token = self._get_token()
        logger.info(f"上传封面: {cover_path}")
        thumb_id = self._upload_thumb(cover_path)

        logger.info("上传正文图片...")
        html = self._replace_images(html, article_dir)

        logger.info("推送草稿...")
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        payload = {
            "articles": [{
                "title": title,
                "author": self.author,
                "content": html,
                "content_source_url": "",
                "thumb_media_id": thumb_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }]
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        data = requests.post(
            url, data=body,
            headers={"Content-Type": "application/json"},
            timeout=30,
        ).json()

        if "media_id" not in data:
            raise RuntimeError(f"推送失败: {data}")

        # 拿预览链接
        preview_url = ""
        try:
            r = requests.post(
                f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}",
                data=json.dumps({"media_id": data["media_id"]}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                timeout=15,
            ).json()
            items = r.get("news_item", [])
            if items:
                preview_url = items[0].get("url", "")
        except Exception:
            pass

        return {"media_id": data["media_id"], "preview_url": preview_url}