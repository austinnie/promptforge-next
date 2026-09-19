# 移植进度表

## 从旧项目搬迁

| 阶段 | 状态 | 内容 |
|---|---|---|
| P0 | 进行中 | 项目骨架 |
| P1 | 待办 | `packages/forge_core/`（预设 / 6 层 / 安全 / 意图） |
| P2 | 待办 | `engines/`（异步化 + registry + dispatcher） |
| P3 | 待办 | `server/` FastAPI 最小接口 |
| P4 | 待办 | Flutter 最小 App |
| P5 | 待办 | 后端地址配置 + 二维码连接 |
| P6 | 待办 | 一键启动 + PyInstaller |
| P7 | 待办 | Skills 按需搬迁 |

## 从旧项目"不搬"清单

- `gui/`（Tkinter）
- `services/pipeline_pool.py`（本地模型）
- `handlers/`（GUI 耦合，逻辑改写进 use_cases）
- `multimedia/`（依赖本地模型，后期重写）
- `config/settings.py`（改 pydantic-settings）
- `output/`（历史产物）
- `.wechat_state.json`、`cookies/*.json`（敏感）
