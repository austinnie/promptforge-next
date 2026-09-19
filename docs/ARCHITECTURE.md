# 架构设计

## 拓扑

~~~
Flutter（5 平台）
    │  HTTP / WS
    ▼
FastAPI（本地 / 云上）
    │
    ▼
第三方 API
~~~

## 三个关键决策

1. **后端独立进程**，不嵌进 Flutter
2. **Flutter 一份代码**，编译 Windows / macOS / Linux / Android / iOS
3. **后端地址可配置**，PC 连 localhost，手机连局域网 IP 或云端

## 目录职责

| 目录 | 职责 | 依赖 |
|---|---|---|
| `packages/forge_core/` | 提示词、预设、安全（纯逻辑） | 无外部依赖 |
| `engines/` | 图像 / 视频 / 文本引擎 | requests, Pillow |
| `server/` | API、编排、任务 | FastAPI |
| `skills/` | 文章、排版、发布等长任务 | 按需 |
| `apps/mobile/` | Flutter | 无 Python |

## 部署模式对照

| 模式 | HOST | 存储 | 数据库 | App 连 |
|---|---|---|---|---|
| PC 本地 | 127.0.0.1 | local | sqlite | localhost:8000 |
| 手机连 PC | 0.0.0.0 | local | sqlite | 192.168.x.x:8000 |
| 云上 | 0.0.0.0 | s3 | postgres | https://api.xxx.com |
