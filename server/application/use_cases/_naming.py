# server/application/use_cases/_naming.py
"""生成可读的存储 key。"""

import re


def make_key(prompt: str, job_id: str, ext: str = "png") -> str:
    """生成可读的文件名。

    格式：{prompt摘要}_{job_id前8位}.{ext}
    例：  "月光下的森林" → "月光下的森林_a1b2c3d4.png"
          ""             → "image_a1b2c3d4.png"
    """
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "_", (prompt or "").strip())
    s = s[:24].strip("_") or "image"
    return f"{s}_{job_id[:8]}.{ext}"