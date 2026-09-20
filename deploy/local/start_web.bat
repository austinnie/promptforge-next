@echo off
chcp 65001 >nul
cd /d "%~dp0\..\.."

set BACKEND_WINDOW=PromptForge Backend
set WEB_WINDOW=PromptForge Web
set WEB_DIR=apps\mobile\build\web

echo ============================================================
echo   PromptForge-Next Web 版一键启动
echo ============================================================

REM ---- 1. 检查 web 产物 ----
if not exist "%WEB_DIR%\index.html" (
    echo [错误] 未找到 Web 编译产物
    echo [提示] 先编译: cd apps\mobile ^&^& flutter build web --release
    pause
    exit /b 1
)

REM ---- 2. 检查 .env ----
if not exist ".env" (
    echo [提示] 未找到 .env，从 .env.sample 复制
    copy .env.sample .env >nul
    echo [警告] 请编辑 .env 填写 AGNES_API_KEY / POLLINATIONS_API_KEY 等
    echo.
    pause
)

REM ---- 3. 起后端 ----
echo [1/3] 启动后端...
start "%BACKEND_WINDOW%" cmd /k "python -m server.run"

timeout /t 3 /nobreak >nul

REM ---- 4. 起 Web 静态服务 ----
echo [2/3] 启动 Web 服务（端口 5000）...
start "%WEB_WINDOW%" cmd /k "cd /d %~dp0\..\..\%WEB_DIR% && python -m http.server 5000"

timeout /t 2 /nobreak >nul

REM ---- 5. 打开浏览器 ----
echo [3/3] 打开浏览器...
start http://localhost:5000

echo.
echo ============================================================
echo   PromptForge-Next 已启动
echo ============================================================
echo   后端:  http://localhost:8000
echo   Web:   http://localhost:5000
echo   两个窗口保持开着，关掉后服务停止
echo ============================================================
exit /b 0