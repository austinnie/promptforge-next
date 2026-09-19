# tests/test_p4_flutter_app.py
# PromptForge · P4 · Flutter 客户端骨架自检
#
# 用法：
#   cd E:\SD_OpenVINO\promptforge-next
#   python tests/test_p4_flutter_app.py
#
# 检查项：
#   1. apps/mobile/ 目录结构（lib/ 子目录 + android/ + ios/）
#   2. 所有 P4 关键文件存在
#   3. pubspec.yaml 依赖齐全
#   4. AndroidManifest.xml 已加 usesCleartextTraffic
#   5. ios/Runner/Info.plist 已加 NSAllowsLocalNetworking
#   6. 若环境有 Flutter SDK，跑一次 flutter analyze
#
# 退出码：0 = 全绿，1 = 有失败项

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# ---------- 路径 ----------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = PROJECT_ROOT / "apps" / "mobile"

# ---------- 期望结构 ----------
REQUIRED_DIRS = [
    "lib",
    "lib/core",
    "lib/models",
    "lib/services",
    "lib/widgets",
    "lib/pages",
    "lib/pages/home",
    "lib/pages/connect",
    "lib/pages/create",
    "lib/pages/jobs",
    "lib/pages/assets",
    "lib/pages/settings",
    "android",           # ← 补齐后应存在
    "ios",               # ← 补齐后应存在
]

REQUIRED_FILES = [
    "pubspec.yaml",
    "lib/main.dart",
    "lib/app.dart",
    "lib/core/app_config.dart",
    "lib/core/theme.dart",
    "lib/models/task.dart",
    "lib/models/work.dart",
    "lib/services/api_client.dart",
    "lib/services/ws_client.dart",
    "lib/services/connection_manager.dart",
    "lib/widgets/status_badge.dart",
    "lib/widgets/preset_picker.dart",
    "lib/pages/home/home_page.dart",
    "lib/pages/connect/connect_page.dart",
    "lib/pages/create/create_page.dart",
    "lib/pages/jobs/jobs_page.dart",
    "lib/pages/assets/assets_page.dart",
    "lib/pages/settings/settings_page.dart",
    # 平台配置
    "android/app/src/main/AndroidManifest.xml",
    "ios/Runner/Info.plist",
]

REQUIRED_DEPS = [
    "http:",
    "web_socket_channel:",
    "shared_preferences:",
    "provider:",
    "mobile_scanner:",
    "qr_flutter:",
    "cached_network_image:",
]

# ---------- 输出工具 ----------
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

_ok_count = 0
_fail_count = 0
_warn_count = 0


def ok(msg: str):
    global _ok_count
    _ok_count += 1
    print(f"{GREEN}  ✓ {msg}{RESET}")


def fail(msg: str):
    global _fail_count
    _fail_count += 1
    print(f"{RED}  ✗ {msg}{RESET}")


def warn(msg: str):
    global _warn_count
    _warn_count += 1
    print(f"{YELLOW}  ! {msg}{RESET}")


def section(title: str):
    print(f"\n── {title} " + "─" * max(2, 50 - len(title)))


# ---------- 检查项 ----------

def check_dirs():
    section("目录结构")
    if not APP_ROOT.exists():
        fail(f"APP_ROOT 不存在: {APP_ROOT}")
        return
    for rel in REQUIRED_DIRS:
        p = APP_ROOT / rel
        if p.is_dir():
            ok(f"dir  {rel}")
        else:
            fail(f"缺少目录 {rel}  →  {p}")


def check_files():
    section("关键文件")
    for rel in REQUIRED_FILES:
        p = APP_ROOT / rel
        if p.is_file():
            ok(f"file {rel}")
        else:
            fail(f"缺少文件 {rel}  →  {p}")


def check_pubspec():
    section("pubspec.yaml 依赖")
    p = APP_ROOT / "pubspec.yaml"
    if not p.is_file():
        fail("pubspec.yaml 不存在，跳过依赖检查")
        return
    text = p.read_text(encoding="utf-8", errors="replace")
    for dep in REQUIRED_DEPS:
        if dep in text:
            ok(f"dep  {dep}")
        else:
            fail(f"缺少依赖 {dep}")


def check_android_manifest():
    section("AndroidManifest.xml")
    p = APP_ROOT / "android/app/src/main/AndroidManifest.xml"
    if not p.is_file():
        fail(f"未找到 {p}")
        return
    text = p.read_text(encoding="utf-8", errors="replace")
    if 'android:usesCleartextTraffic="true"' in text:
        ok("usesCleartextTraffic=true 已配置")
    else:
        fail('AndroidManifest 缺少 android:usesCleartextTraffic="true"')


def check_ios_plist():
    section("ios/Runner/Info.plist")
    p = APP_ROOT / "ios/Runner/Info.plist"
    if not p.is_file():
        fail(f"未找到 {p}")
        return
    text = p.read_text(encoding="utf-8", errors="replace")
    if "NSAllowsLocalNetworking" in text and "NSAppTransportSecurity" in text:
        ok("NSAllowsLocalNetworking 已配置")
    else:
        fail("Info.plist 缺少 NSAppTransportSecurity / NSAllowsLocalNetworking")


def check_flutter_sdk() -> bool:
    section("Flutter SDK")
    exe = shutil.which("flutter")
    if not exe:
        warn("未在 PATH 找到 flutter，跳过 analyze（安装 SDK 后可重跑）")
        return False
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
        first = (r.stdout or "").splitlines()[0] if r.stdout else "flutter"
        ok(f"发现 {first.strip()}")
        return True
    except Exception as e:
        warn(f"flutter --version 执行异常: {e}")
        return False


def run_flutter_analyze(has_sdk: bool):
    section("flutter analyze")
    if not has_sdk:
        warn("跳过 flutter analyze")
        return

    # Windows 上 flutter 实际是 flutter.bat，subprocess 不会自动带 .bat，
    # 用 shutil.which 拿到完整路径再传进去
    flutter_exe = shutil.which("flutter")
    if not flutter_exe:
        warn("找不到 flutter 可执行文件")
        return

    try:
        r = subprocess.run(
            [flutter_exe, "analyze"],
            cwd=str(APP_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            ok("flutter analyze 通过")
        else:
            fail("flutter analyze 有报错")
            # 直接打印前 200 行，别过滤，防止漏掉非 error 前缀的提示
            for line in out.splitlines()[:200]:
                print(f"      {line}")
    except subprocess.TimeoutExpired:
        warn("flutter analyze 超时（>5min），可能有首次索引编译")
    except Exception as e:
        warn(f"flutter analyze 执行异常: {e}")


# ---------- 主流程 ----------

def main():
    print("\n" + "=" * 62)
    print("  P4 · Flutter 客户端骨架自检")
    print(f"  目标: {APP_ROOT}")
    print("=" * 62)

    check_dirs()
    check_files()
    check_pubspec()
    check_android_manifest()
    check_ios_plist()
    has_sdk = check_flutter_sdk()
    run_flutter_analyze(has_sdk)

    print("\n" + "=" * 62)
    print(f"  结果: {GREEN}{_ok_count} 通过{RESET}  "
          f"{RED}{_fail_count} 失败{RESET}  "
          f"{YELLOW}{_warn_count} 警告{RESET}")
    print("=" * 62)

    if _fail_count == 0:
        print(f"\n{GREEN}✅ P4 骨架就绪{RESET}")
        print("   下一步: cd apps/mobile && flutter pub get && flutter run -d windows")
        return 0
    else:
        print(f"\n{RED}❌ 有 {_fail_count} 项未通过，按上面 ✗ 提示逐项处理{RESET}")
        print("   常见原因：")
        print("     1. 缺 android/ios/ 目录 → cd apps/mobile && flutter create --platforms android,ios .")
        print("     2. test/widget_test.dart 还在 → rmdir /s /q apps\\mobile\\test")
        print("     3. lib/ 下有 dart 语法/类型错误 → 按 analyze 输出逐条修")
        return 1


if __name__ == "__main__":
    sys.exit(main())