# server/run.py
"""本地启动脚本：python -m server.run"""

import socket

import uvicorn

from server.core.config import settings


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main():
    print("=" * 60)
    print("  PromptForge-Next Backend")
    print("=" * 60)
    print(f"  部署模式 : {settings.deployment}")
    print(f"  监听     : {settings.host}:{settings.port}")
    print(f"  存储     : {settings.storage_backend}")
    print(f"  安全检测 : {'开启' if settings.enable_safety_check else '关闭'}")
    print()

    if settings.host == "0.0.0.0":
        local_ip = get_local_ip()
        print(f"  本机访问 : http://127.0.0.1:{settings.port}")
        print(f"  局域网   : http://{local_ip}:{settings.port}")
        print(f"  📱 手机连 PC 用这个地址")
    else:
        print(f"  访问     : http://127.0.0.1:{settings.port}")
        print(f"  💡 想手机连 PC，把 .env 里 HOST 改成 0.0.0.0")

    print(f"  文档     : http://127.0.0.1:{settings.port}/docs")
    print("=" * 60)

    uvicorn.run(
        "server.main:app",
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()