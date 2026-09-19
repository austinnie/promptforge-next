#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../.."

echo "🚀 启动 PromptForge 后端..."
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
