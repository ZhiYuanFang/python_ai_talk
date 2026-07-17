## Why

当前 python_ai_talk 的意图分析接口（`/analyze/intent`）只做意图分类，没有根据意图类型动态拉取历史数据和向量库知识。当用户询问"今天喝了多少奶粉"或"宝宝最近食量怎么样"时，系统无法获取相关历史数据来生成有意义的回答。同时，go_ai_talk 的 history-service 现有 API 不支持按事件类型筛选历史记录，Python 侧只能拉全量数据后过滤，效率低下。

## What Changes

- **Go 侧新增 API**: 在 go_ai_talk 的 history-service 中新增 `/device/history/api/filter` 接口，支持按事件ID列表（多个，事件ID不变而名称会变）和时间范围筛选历史记录
- **Python 侧意图后处理**: 修改 `analyze_intent` 接口，在意图分类后增加"后处理"阶段：
  - `history` 意图：调用 LLM 判断需要的事件ID和时间范围 → 调用新 API 拉取历史 → 调用 LLM 生成回答
  - `suggest` 意图：调用 LLM 判断需要的事件ID和时间范围 → 调用新 API 拉取历史 + 向量检索 + 宝宝画像 → 调用 LLM 生成建议
  - `feeding` 意图：保持不变（直接返回，Go 侧处理 CRUD）
  - `conversation` 意图：保持不变（兜底文案）
- **Python 侧 HTTP 客户端**: 新增 `get_filtered_history_events` 方法，调用 go 侧新 API

## Capabilities

### New Capabilities

- `history-filter-api`: Go 侧新增历史记录筛选 API，支持多事件ID + 时间范围筛选
- `intent-post-processing`: Python 侧意图分析后处理逻辑，根据意图类型动态拉取数据并生成回答

### Modified Capabilities

- `intent-analysis`: 修改意图分析接口，增加 history/suggest 意图的后处理逻辑

## Impact

**Go 项目 (go_ai_talk) 修改**:
- `internal/controller/device_history.go`: 新增 `Filter` 方法
- `internal/model/api/v1/`: 新增请求/响应模型定义
- `internal/services/contracts/`: 新增服务契约方法
- `internal/services/history/`: 实现过滤查询逻辑

**Python 项目 (python_ai_talk) 修改**:
- `app/api/routes.py`: 修改 `analyze_intent`，增加意图后处理阶段
- `app/services/http_client.py`: 新增 `get_filtered_history_events` 方法
- `app/services/llm_client.py`: 新增动态判断历史数据需求的提示词构建

**API 影响**:
- 新增 Go API: `GET /device/history/api/filter`
- Python 接口返回结构保持不变，但 `content` 字段在 history/suggest 场景下会包含 LLM 生成的回答内容
