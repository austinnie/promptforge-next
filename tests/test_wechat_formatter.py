#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""wechat_formatter 验收。"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from skills.wechat_formatter import WechatFormatter  # noqa: E402


# 用变量拼出三反引号，避免破坏源码里的 markdown 结构
TRIPLE = "`" * 3

SAMPLE_MD = (
    "# 测试文章\n\n"
    "在数字化时代，**内容创作**变得越来越重要。\n\n"
    "> 好的排版不只是视觉享受，更是对读者的尊重。\n\n"
    "## 主要功能\n\n"
    "- 完整的 Markdown 语法支持\n"
    "- 精美的主题样式\n"
    "- 一键复制到微信发布\n\n"
    "### 代码示例\n\n"
    f"{TRIPLE}python\n"
    "def hello():\n"
    "    print(\"Hello, World!\")\n"
    f"{TRIPLE}\n\n"
    "| 功能 | 状态 |\n"
    "|------|------|\n"
    "| 实时预览 | 已支持 |\n"
    "| 主题选择 | 已支持 |\n\n"
    "## 小结\n\n"
    "这是一段普通文字，用来验证排版后**加粗**和*斜体*都能正常渲染。\n"
)


async def main():
    print("=" * 60)
    print("  wechat_formatter 验收")
    print("=" * 60)

    fmt = WechatFormatter()

    # 1. 列主题
    print("\n[1] list_themes")
    r = await fmt.execute(action="list_themes")
    if r["status"] == "success":
        print(f"    主题数: {r['result']['count']}")
        for t in r["result"]["themes"][:5]:
            print(f"      {t['id']:20} {t['name']}")
    else:
        print(f"    错误: {r['error']}")

    # 2. 单主题排版
    print("\n[2] format（单主题 terracotta）")
    r = await fmt.execute(
        action="format",
        content=SAMPLE_MD,
        theme="terracotta",
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    标题: {res['title']}")
        print(f"    字数: {res['word_count']}")
        print(f"    主题: {res['theme_name']}")
        print(f"    文章: {res['article_path']}")
        print(f"    预览: {res['preview_path']}")
        print(f"    耗时: {res['elapsed']}")
    else:
        print(f"    错误: {r['error']}")

    # 3. 画廊模式
    print("\n[3] format（画廊模式）")
    r = await fmt.execute(
        action="format",
        content=SAMPLE_MD,
        gallery=True,
    )
    print(f"    状态: {r['status']}")
    if r["status"] == "success":
        res = r["result"]
        print(f"    主题数: {res['theme_count']}")
        print(f"    画廊: {res['gallery_path']}")
    else:
        print(f"    错误: {r['error']}")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())