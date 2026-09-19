# API 清单

Base: `/api/v1`

## 系统

- `GET /system/info` — 本机 IP、端口、部署模式

## 引擎

- `GET /engines` — 列出所有引擎及其能力

## 预设

- `GET /presets` — 列出所有预设（按分类）
- `GET /presets/{name}` — 单个预设详情

## 任务

- `POST /jobs/image` — 创建生图任务
- `POST /jobs/image-to-image` — 图生图
- `POST /jobs/video` — 视频
- `GET  /jobs/{id}` — 查询
- `DELETE /jobs/{id}` — 取消

## 实时

- `WS /jobs/{id}/events` — 任务进度

## 作品

- `GET /assets` — 作品列表
- `GET /assets/{id}` — 详情
- `DELETE /assets/{id}` — 删除

## 文件（本地存储）

- `GET /files/{key}` — 静态文件
