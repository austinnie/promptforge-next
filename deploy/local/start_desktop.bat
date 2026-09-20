@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0\..\.."

set BACKEND_WINDOW=PromptForge Backend
set DESKTOP_EXE=apps\mobile\build\windows\x64\runner\Release\promptforge_mobile.exe

echo ============================================================
echo   PromptForge-Next 桌面版一键启动
echo ============================================================

REM ---- 1. 检查 exe ----
if not exist "%DESKTOP_EXE%" (
    echo [错误] 未找到桌面版 exe
    echo [提示] 先编译: cd apps\mobile ^&^& flutter build windows --release
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

REM ---- 3. 起后端（新窗口） ----
echo [1/3] 启动后端...
start "%BACKEND_WINDOW%" cmd /k "python -m server.run"

REM ---- 4. 等后端就绪（最多 20 秒） ----
echo [2/3] 等待后端就绪...
set READY=0
for /l %%i in (1,1,20) do (
    if !READY!==0 (
        timeout /t 1 /nobreak >nul
        curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8000/api/v1/system/info > "%TEMP%\pf_status.txt" 2>nul
        set /p CODE=<"%TEMP%\pf_status.txt"
        if "!CODE!"=="200" (
            set READY=1
            echo [就绪] 后端已就绪
        )
    )
)

if "!READY!"=="0" (
    echo [警告] 后端未在 20 秒内就绪，但继续启动前端
)

REM ---- 5. 起桌面版 ----
echo [3/3] 启动桌面版...
start "" "%DESKTOP_EXE%"

echo.
echo ============================================================
echo   PromptForge-Next 已启动
echo ============================================================
echo   后端窗口: 保持开着，关掉后 App 会离线
echo   桌面 App: 已经打开
echo ============================================================
exit /b 0