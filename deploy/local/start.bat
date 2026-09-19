@echo off
chcp 65001 >nul
cd /d "%~dp0\..\.."

echo 🚀 启动 PromptForge 后端...
start "PromptForge Backend" cmd /k "python -m uvicorn server.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul
echo.
echo ✅ 后端已启动: http://localhost:8000/docs
echo 📱 手机连 PC：查看后端启动日志里的局域网地址
pause
