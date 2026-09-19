#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""dispatcher 全能力验收：t2i / i2i / chat / vision / audio / video。

用法：
    python tests/test_dispatcher_full.py

说明：
    - 每一项独立 try/except，单项失败不影响其他项
    - 无 key 的能力会跳过并提示
    - video 默认关闭（耗时久），用 --video 显式开启
"""

import argparse
import asyncio
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engines  # noqa: E402
from engines import dispatcher  # noqa: E402

OUT_DIR = ROOT / "data" / "assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def test_t2i():
    print("\n[1] t2i")
    try:
        img, used = await dispatcher.generate_image(
            "a lone lighthouse on a cliff, stormy sea, cinematic",
            width=768, height=768,
        )
        out = OUT_DIR / "disp_t2i.png"
        img.save(out)
        print(f"    ✅ {used} | {img.size} | {out.relative_to(ROOT)}")
        return img
    except Exception as e:
        print(f"    ❌ {str(e)[:200]}")
        return None


async def test_i2i(base_img):
    print("\n[2] i2i")
    if base_img is None:
        print("    ⬜ 跳过（无 t2i 底图）")
        return
    try:
        img, used = await dispatcher.image_to_image(
            prompt="make it look like an oil painting, Van Gogh style",
            image=base_img,
            strength=0.7,
            width=768, height=768,
        )
        out = OUT_DIR / "disp_i2i.png"
        img.save(out)
        print(f"    ✅ {used} | {img.size} | {out.relative_to(ROOT)}")
    except Exception as e:
        print(f"    ❌ {str(e)[:200]}")


async def test_chat():
    print("\n[3] chat")
    try:
        text, used = await dispatcher.chat(
            messages=[
                {"role": "user",
                 "content": "用一句话描述'赛博朋克雨夜'，不超过30字"}
            ],
            max_tokens=200,
        )
        print(f"    ✅ {used} | {text[:120]}")
    except Exception as e:
        print(f"    ❌ {str(e)[:200]}")


async def test_vision(base_img):
    print("\n[4] vision（图片反推）")
    if base_img is None:
        print("    ⬜ 跳过（无底图）")
        return
    try:
        text, used = await dispatcher.image_to_text(
            image=base_img,
            prompt="用一句话描述这张图片的主要内容",
        )
        print(f"    ✅ {used} | {text[:150]}")
    except Exception as e:
        print(f"    ❌ {str(e)[:200]}")


async def test_audio():
    print("\n[5] audio（TTS）")
    try:
        audio, used = await dispatcher.generate_audio(
            text="你好，这里是 PromptForge，多引擎提示词编排系统。",
            voice="alloy",
            output_format="mp3",
        )
        out = OUT_DIR / "disp_tts.mp3"
        out.write_bytes(audio)
        print(f"    ✅ {used} | {len(audio) // 1024} KB | {out.relative_to(ROOT)}")
    except Exception as e:
        print(f"    ❌ {str(e)[:200]}")


async def test_video():
    print("\n[6] video（会耗时 1-3 分钟）")
    try:
        video, used = await dispatcher.generate_video(
            prompt="a serene mountain lake at sunrise, slow camera pan",
            duration=5,
            width=768, height=768,
            max_wait=600,
        )
        out = OUT_DIR / "disp_video.mp4"
        out.write_bytes(video)
        print(f"    ✅ {used} | {len(video) // 1024} KB | {out.relative_to(ROOT)}")
    except Exception as e:
        print(f"    ❌ {str(e)[:200]}")


async def main(run_video: bool):
    print("=" * 60)
    print("  dispatcher 全能力验收")
    print("=" * 60)

    print("\n[0] 降级链")
    for cap, chain in dispatcher.describe_chain().items():
        print(f"    {cap:8} → {' → '.join(chain) or '(空)'}")

    base = await test_t2i()
    await test_i2i(base)
    await test_chat()
    await test_vision(base)
    await test_audio()
    if run_video:
        await test_video()
    else:
        print("\n[6] video")
        print("    ⬜ 默认跳过（加 --video 参数开启）")

    print("\n" + "=" * 60)
    print("  完成")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", action="store_true", help="跑视频生成（耗时）")
    args = parser.parse_args()
    asyncio.run(main(args.video))