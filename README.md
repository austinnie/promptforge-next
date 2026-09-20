# PromptForge-Next

智能提示词 + 多引擎 API 编排系统。

- **前端**：Flutter（Windows / macOS / Linux / Android / iOS 一份代码）
- **后端**：FastAPI（本地跑 / 云上跑，同一份代码）
- **模型**：不跑本地 SD，只调用第三方 API（Agnes / Pollinations / SiliconFlow / OpenRouter 等）
- **核心价值**：100+ 预设 + 6 层提示词系统 + 意图分析 + 多引擎自动降级

## 快速开始

### 1. 后端

~~~bash
pip install -r requirements-server.txt
python -m server.run
或者
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
~~~

启动后：

- 本机文档：http://localhost:8000/docs
- 手机连 PC：查看日志里的局域网地址，如 http://192.168.1.42:8000

### 2. 前端（另开终端）

~~~bash
cd apps/mobile
flutter pub get
flutter run -d chrome
flutter run -d web
flutter run -d windows      # Windows 桌面
flutter run -d macos        # macOS
flutter run -d linux        # Linux
flutter run                 # 连 Android/iOS 真机


flutter devices      # 看手机连没连上
flutter run -d <手机ID>   # 直接推送到手机，支持热重载
~~~

## 目录结构

~~~
apps/mobile/            Flutter 前端（5 平台）
server/                 FastAPI 后端
packages/forge_core/    纯逻辑（提示词 / 预设 / 安全）
engines/                图像 / 视频 / 文本引擎（异步）
skills/                 文章、排版、发布等长任务
deploy/                 本地 & 云端部署配置
data/                   运行时数据（本地存储 / sqlite）
docs/                   文档
~~~

## 三种部署模式

| 模式 | HOST | 存储 | 数据库 | App 连 |
|---|---|---|---|---|
| PC 本地 | 127.0.0.1 | local | sqlite | localhost:8000 |
| 手机连 PC | 0.0.0.0 | local | sqlite | 192.168.x.x:8000 |
| 云上 | 0.0.0.0 | s3 | postgres | https://api.xxx.com |

## 文档

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 整体架构
- [docs/MIGRATION.md](docs/MIGRATION.md) — 从旧项目移植进度
- [docs/API.md](docs/API.md) — 后端接口清单
