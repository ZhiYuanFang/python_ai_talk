## Why

当前 python_ai_talk 项目存在三个核心问题：1) 声明了 LangGraph 依赖但未实际使用，`langchain-openai` 仅作为 HTTP 客户端包装器；2) 所有路由逻辑堆叠在单个 `routes.py` 中，意图分析和诊疗流程无复用；3) 缺少意图后处理——history/suggest 意图只做分类不生成回答，clinic 场景拉全量历史无动态筛选。同时 go_ai_talk 的 history-service 不支持按事件ID筛选历史记录，导致 Python 侧只能拉全量数据后过滤。

## What Changes

- **Go 侧新增 Filter API**: 在 go_ai_talk 的 history-service 中新增 `/device/history/api/filter` 接口，支持按事件ID列表（事件ID不变而名称会变）和时间范围筛选历史记录
- **LangGraph 编排重构**: 用 LangGraph StateGraph 编排意图分析和诊疗流程，替代当前手写 if/else 逻辑
- **接口路由分文件**: 拆分 `routes.py` 为 `routes/intent.py`、`routes/clinic.py`、`routes/health.py`
- **共享节点抽取**: 将可复用逻辑封装为独立节点文件（一节点一文件），包括：意图分类、数据需求判断、历史拉取、向量检索、宝宝画像获取、回答生成
- **提示词独立管理**: 将 prompt 构建函数从路由中抽离到 `graphs/nodes/prompts/` 目录
- **State 分离定义**: intent_graph 和 clinic_graph 各自独立的 State 类
- **意图后处理实现**: history 意图→判断数据需求→拉取历史→LLM 生成回答；suggest 意图→判断数据需求→拉取历史+向量检索+宝宝画像→LLM 生成建议
- **clinic 动态判断历史范围**: 诊疗场景也复用 `judge_data_requirement` 节点，按需拉取历史而非全量
- **Python 侧 HTTP 客户端**: 新增 `get_filtered_history_events` 方法，调用 Go 侧新 API

## Capabilities

### New Capabilities

- `history-filter-api`: Go 侧新增历史记录筛选 API，支持多事件ID + 时间范围筛选
- `langgraph-intent-graph`: 基于 LangGraph 的意图分析状态图，包含意图分类→路由→后处理完整流程
- `langgraph-clinic-graph`: 基于 LangGraph 的诊疗状态图，包含数据需求判断→历史拉取→向量检索→流式回答流程
- `shared-graph-nodes`: 可复用的 LangGraph 节点集合（classify_intent, judge_data_requirement, fetch_history, search_vectors, fetch_baby_profile, generate_response, stream_response）

### Modified Capabilities

- `intent-analysis`: 意图分析接口从手写逻辑改为 LangGraph 编排，增加 history/suggest 意图后处理
- `clinic-stream`: 诊疗接口从手写逻辑改为 LangGraph 编排，增加动态历史范围判断

## Impact

**Go 项目 (go_ai_talk) 修改**:
- `internal/controller/device_history.go`: 新增 `Filter` 方法
- `internal/model/api/v1/`: 新增请求/响应模型定义
- `internal/services/contracts/`: 新增服务契约方法
- `internal/services/history/`: 实现过滤查询逻辑

**Python 项目 (python_ai_talk) 修改**:
- **新增目录**:
  - `app/api/routes/` (拆分路由)
  - `app/graphs/` (状态图)
  - `app/graphs/nodes/` (共享节点)
  - `app/graphs/nodes/prompts/` (提示词)
  - `app/graphs/states/` (State 定义)
- **修改文件**:
  - `app/api/routes.py` → 拆分为多文件
  - `app/services/http_client.py` → 新增 `get_filtered_history_events` 方法
- **删除文件**:
  - `app/api/routes.py` (旧文件，逻辑迁移到 graphs + routes/)
- **依赖变更**:
  - `langgraph` 依赖从声明未用变为实际使用
  - 移除 `langchain-openai` 对 `langchain.schema` 消息类的依赖，改用 LangGraph 原生方式

**API 影响**:
- 新增 Go API: `GET /device/history/api/filter`
- Python 接口路径不变（`/v1/analyze/intent`, `/v1/clinic/stream`），但内部实现完全重构
- Python 接口返回结构保持兼容，history/suggest 场景的 `content` 字段会包含 LLM 生成的回答
