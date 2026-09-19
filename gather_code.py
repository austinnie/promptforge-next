#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将当前项目所有代码文件合并为一个 txt 文件。

用法:
    python gather_code.py
输出:
    project_code_dump.txt  (保存在项目根目录)
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# ==================== 配置区 ====================

# 要包含的扩展名（小写，含点）
INCLUDE_EXTS = {
    # 代码
    '.py', '.js', '.ts', '.html', '.css', '.vue', '.jsx', '.tsx',
    # 配置 / 数据
    '.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.conf',
    '.xml', '.env', '.properties',
    # 文档
    '.md', '.txt', '.rst',
    # 其他
    '.gitignore', '.gitattributes', '.editorconfig', '.dockerignore',
    '.sh', '.bat', '.ps1',
}

# 要包含的无扩展名文件（完全匹配）
INCLUDE_NAMES = {
    'Dockerfile', 'Makefile', 'LICENSE', 'README', 'CHANGELOG',
    '.env.sample', '.env.example',
}

# 排除的目录（完全匹配，任意层级的同名目录都会跳过）
EXCLUDE_DIRS = {
    # 缓存 / 环境
    '__pycache__', '.git', '.svn', '.hg', '.venv', 'venv', 'env',
    '.env', 'node_modules', '__pypackages__',
    # IDE
    '.idea', '.vscode', '.vs',
    # 构建产物
    'dist', 'build', 'target', '.next', '.nuxt',
    '*.egg-info',
    # 项目生成物（如需包含，请注释掉下面几行）
    'output',
    'outputs',
    'logs',
    'tmp',
    'temp',
    'cache',
    '.cache',
    '.pytest_cache',
    'htmlcov',
    '.mypy_cache',
    '.ruff_cache',
    # 打包生成物
    'code_collect_report',
    'social_auto_upload.egg-info',
    # 静态素材（体积大、非代码）
    'assets',
    'soundfonts',
    'images',
    'img',
    'media',
    'videos',
    'audio',
    'fonts',
    'models',
    'checkpoints',
}

# 排除的具体文件（完全匹配，包括文件名和相对路径两种写法）
EXCLUDE_FILES = {
    # 敏感信息
    '.env',
    '.env.local',
    '.env.production',
    '.user_config.json',
    '.wechat_state.json',
    '.cache.json',
    'lora_config',
    '.model_config',
    'cookies',                 # social_auto_upload 的 cookies 目录
    # 大文件 / 二进制
    'project_code_dump.txt',
    'gather_code.py.bak',
    'package-lock.json',
    'yarn.lock',
    'poetry.lock',
    'Pipfile.lock',
}

# 排除的路径前缀（相对项目根，匹配则跳过）
EXCLUDE_PREFIXES = {
    '.git/',
    'output/',
    'outputs/',
    'logs/',
    '.venv/',
    'venv/',
    'node_modules/',
    # social_auto_upload 的 cookies 目录
    'skills/social_auto_upload/cookies/',
    'skills/social_auto_upload/logs/',
    'skills/social_auto_upload/uploadFile/',
    'skills/social_auto_upload/videoFile/',
    'skills/social_auto_upload/cookiesFile/',
}

# 单文件大小上限（字节）；超过跳过，防止把 model / dump 塞进来
MAX_FILE_SIZE = 2 * 1024 * 1024      # 2 MB

# 总输出大小上限（字节）；超过截断并提示
MAX_TOTAL_SIZE = 20 * 1024 * 1024    # 20 MB

# 输出文件名
OUTPUT_FILE = "project_code_dump.txt"

# ==================== 核心逻辑 ====================


def _norm(p: Path) -> str:
    """统一成 POSIX 风格相对路径，便于做前缀匹配。"""
    return str(p).replace("\\", "/")


def should_include_file(file_path: Path, root_dir: Path) -> bool:
    """判断某个文件是否应该被收集。"""
    try:
        rel = file_path.relative_to(root_dir)
    except ValueError:
        return False

    rel_posix = _norm(rel)

    # 1) 相对路径前缀排除
    for prefix in EXCLUDE_PREFIXES:
        if rel_posix.startswith(prefix):
            return False

    # 2) 任意祖先目录名命中排除列表
    for parent in rel.parents:
        if parent == Path("."):
            continue
        if parent.name in EXCLUDE_DIRS:
            return False
        # 支持 *.egg-info 这类通配
        for pat in EXCLUDE_DIRS:
            if pat.startswith("*") and parent.name.endswith(pat[1:]):
                return False

    # 3) 文件名排除（完全匹配 rel 或 name）
    if rel_posix in EXCLUDE_FILES or file_path.name in EXCLUDE_FILES:
        return False

    # 4) 明确无扩展名的白名单文件
    if file_path.name in INCLUDE_NAMES:
        return True

    # 5) 扩展名匹配
    ext = file_path.suffix.lower()
    if ext and ext in INCLUDE_EXTS:
        return True

    # 6) 无扩展名但以 . 开头（例如 .gitignore 这种已在扩展名列表里的，前面已命中）
    #    其余无扩展名文件不再收集
    return False


def gather_files(root_dir: Path) -> list:
    """递归收集所有符合条件的文件路径。"""
    files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 原地修改 dirnames，跳过排除目录（能显著减少遍历量）
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS
            and not (d.startswith(".") and d not in {".github", ".vscode"})
        ]

        for name in filenames:
            fp = Path(dirpath) / name
            if should_include_file(fp, root_dir):
                try:
                    if fp.stat().st_size > MAX_FILE_SIZE:
                        print(f"  ⏭️  跳过（超 {MAX_FILE_SIZE // 1024}KB）: {_norm(fp.relative_to(root_dir))}")
                        continue
                except OSError:
                    continue
                files.append(fp)

    files.sort(key=lambda p: _norm(p.relative_to(root_dir)).lower())
    return files


def read_text_safe(fp: Path) -> str:
    """尽最大努力读取文本，兼容多种编码。"""
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return fp.read_text(encoding=enc, errors="strict")
        except (UnicodeDecodeError, LookupError):
            continue
        except Exception as e:
            return f"[读取失败: {e}]"
    # 最后一次带 replace
    try:
        return fp.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[读取失败: {e}]"


def main():
    root = Path.cwd()
    print(f"📂 扫描目录: {root}")

    files = gather_files(root)
    if not files:
        print("⚠️  未找到任何符合条件的文件，请检查 INCLUDE_EXTS / EXCLUDE_DIRS 配置。")
        return 1

    print(f"📄 找到 {len(files)} 个文件，正在写入 {OUTPUT_FILE} ...")

    out_path = root / OUTPUT_FILE
    total_bytes = 0
    written = 0
    skipped_big = 0

    with open(out_path, "w", encoding="utf-8", errors="replace", newline="\n") as out_f:
        header = (
            f"项目代码汇总 (扫描于 {root})\n"
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"包含文件数: {len(files)}\n"
            + "=" * 80 + "\n\n"
        )
        out_f.write(header)
        total_bytes += len(header.encode("utf-8"))

        for fp in files:
            rel = _norm(fp.relative_to(root))
            content = read_text_safe(fp)

            chunk = (
                f"=== 文件: {rel} ===\n"
                f"{content}\n"
                "\n\n" + "-" * 40 + "\n\n"
            )
            chunk_bytes = len(chunk.encode("utf-8"))

            if total_bytes + chunk_bytes > MAX_TOTAL_SIZE:
                skipped_big += 1
                out_f.write(f"=== 文件: {rel} ===\n[跳过：累计输出已达上限 {MAX_TOTAL_SIZE // 1024 // 1024}MB]\n\n" + "-" * 40 + "\n\n")
                continue

            out_f.write(chunk)
            total_bytes += chunk_bytes
            written += 1

    size_kb = out_path.stat().st_size // 1024
    print(f"✅ 完成！写入 {written} 个文件")
    print(f"   输出文件: {out_path}")
    print(f"   文件大小: {size_kb} KB")
    if skipped_big:
        print(f"   ⚠️  因总大小上限跳过 {skipped_big} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())