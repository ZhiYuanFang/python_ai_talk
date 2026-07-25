## Why

Python 项目 `http_client.py` 中调用的 4 个兄弟仓接口路径全部与 Go 项目（go_ai_talk）实际存在的接口不匹配，导致所有 HTTP 调用都会 404。具体问题：
- 事件字典接口：路径 `/api/events/dictionary` → 实际应为 `/device/history/api/event/options`
- 全量历史接口：路径 `/api/events/list` → 实际应为 `/device/history/api/list`，且参数体系不同（Python 用时间范围+limit，Go 用分页）
- 筛选历史接口：路径 `/device/history/api/filter` → Go 中不存在此接口（仅有单事件区段查询 piece，不支持多 eventIds）
- 宝宝画像接口：路径 `/api/device/{device_no}/baby` → 实际应为 `/device/history/api/birthday`

这些问题导致 Python 服务与 Go 兄弟仓完全无法通信，所有依赖外部数据的功能（意图分析、喂养建议、诊疗建议）均不可用。

## What Changes

- 修复 `app/shared/http_client.py` 中 4 个接口的路径，对齐 Go 实际接口
- 适配 Go 侧返回的数据格式（外层 list 包装、camelCase 字段名）
- 适配 Go 侧参数传递方式（path vs query）
- 新增降级逻辑：Go 侧 filter 接口尚未就绪时，Python 侧用全量拉取 + 本地过滤替代
- 在 Go 侧新增历史筛选接口 `/device/history/api/filter`（支持多 eventIds + 时间范围 + limit）
- 在 Go 侧扩展 `/device/history/api/list` 接口，增加 startTime、endTime、limit 可选参数

## Capabilities

### New Capabilities

- **历史筛选接口**：Go 侧新增 `GET /device/history/api/filter`，支持按设备号、多事件ID列表、时间范围、返回条数上限筛选历史记录
- **全量历史时间范围查询**：Go 侧扩展 `GET /device/history/api/list`，支持 startTime、endTime、limit 可选参数

### Modified Capabilities

- **Python HTTP 客户端**：所有 4 个兄弟仓接口路径、参数、返回值解析对齐 Go 实际接口
- **向后兼容**：Go 侧 list 接口新增参数均为可选，不传时保持原有分页行为不变

## Impact

- **Python 代码文件**：`app/shared/http_client.py`（4 个方法路径 + 参数 + 返回值解析）
- **Go 代码文件**：history-service 需新增 filter 接口，扩展 list 接口
- **依赖**：Go 侧需先部署 filter 接口，Python 侧 filter API 才能跳过降级
- **无破坏性变更**：所有 Go 侧改动均为新增或可选扩展，不影响现有调用方
