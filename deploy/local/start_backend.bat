@echo off
chcp 65001 >nul
cd /d "%~dp0\..\.."

echo ============================================================
echo   PromptForge-Next 后端
echo ============================================================

REM ---- 1. 检查 Python ----
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM ---- 2. 检查依赖 ----
python -c "import fastapi, uvicorn, PIL, requests" >nul 2>nul
if errorlevel 1 (
    echo [提示] 首次运行，安装后端依赖...
    python -m pip install -r requirements-server.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

REM ---- 3. 检查 .env ----
if not exist ".env" (
    echo [提示] 未找到 .env，从 .env.sample 复制
    copy .env.sample .env >nul
    echo [警告] 请编辑 .env 填写 AGNES_API_KEY / POLLINATIONS_API_KEY 等
    echo.
    pause
)

REM ---- 4. 起后端 ----
echo [启动] 后端监听 http://0.0.0.0:8000
echo [提示] 手机连 PC 用日志里的"局域网"地址
echo.
python -m server.run

pause