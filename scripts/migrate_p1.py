#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
P1 迁移：把旧项目里的"数据资产"拷进 forge_core。

- presets/           → packages/forge_core/presets/
- layers/            → packages/forge_core/layers/
- presets_meta.py    → packages/forge_core/presets_meta.py

只拷数据，不拷依赖 GUI / 本地模型的文件。
敏感文件（cookies/*.json、.wechat_state.json）会被显式跳过。
"""

import argparse
import shutil
import sys
from pathlib import Path

# 这些文件绝对不拷
BLACKLIST_NAMES = {
    ".wechat_state.json",
    ".env",
    ".env.local",
    ".user_config.json",
    "cookies",
}

SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", "output"}


def is_blacklisted(path: Path) -> bool:
    for part in path.parts:
        if part in BLACKLIST_NAMES:
            return True
        if part in SKIP_DIRS:
            return True
    if path.suffix == ".pyc":
        return True
    return False


def copy_tree(src: Path, dst: Path, label: str) -> int:
    if not src.exists():
        print(f"  ⚠️ 源目录不存在: {src}")
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        if is_blacklisted(item):
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)
        count += 1
    print(f"  ✅ {label}: 拷贝 {count} 个文件 → {dst}")
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", required=True, help="旧项目根目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不实际拷贝")
    args = parser.parse_args()

    old_root = Path(args.old).resolve()
    new_root = Path(__file__).resolve().parents[1]

    if not old_root.exists():
        print(f"❌ 旧项目不存在: {old_root}")
        sys.exit(1)

    print(f"📦 旧项目: {old_root}")
    print(f"📦 新项目: {new_root}")
    print()

    core = new_root / "packages" / "forge_core"

    if args.dry_run:
        print("(dry-run)")
        return

    # 1. presets/
    copy_tree(old_root / "presets", core / "presets", "presets/")

    # 2. layers/
    copy_tree(old_root / "layers", core / "layers", "layers/")

    # 3. presets_meta.py（单文件）
    src_meta = old_root / "presets_meta.py"
    dst_meta = core / "presets_meta.py"
    if src_meta.exists():
        # 只拷原始数据文件，用户稍后手动改 get_presets_by_category
        shutil.copy2(src_meta, dst_meta)
        print(f"  ✅ presets_meta.py → {dst_meta}")
        print(f"     ⚠️ 请手动改文件末尾的 get_presets_by_category（见 P1 说明）")
    else:
        print(f"  ⚠️ 未找到 {src_meta}")

    # 4. 清理 presets/ 下的 __pycache__ 和 __init__.py（旧的可能为空）
    for p in (core / "presets").glob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)

    print()
    print("🎉 P1 数据迁移完成。")
    print()
    print("接下来手动创建 forge_core 里的代码文件（见 Part B）：")
    print("  packages/forge_core/__init__.py")
    print("  packages/forge_core/loader.py")
    print("  packages/forge_core/composer.py")
    print("  packages/forge_core/safety.py")
    print("  packages/forge_core/prompt_builder.py")
    print("  packages/forge_core/context_manager.py")
    print("  packages/forge_core/preset_bridge.py")
    print("  packages/forge_core/intent.py")
    print()
    print("⚠️ 别忘了改 presets_meta.py 的末尾，见 P1 Part B 说明。")


if __name__ == "__main__":
    main()