## Context

当前 python_ai_talk 项目存在架构和功能两方面的缺陷：

**架构缺陷**：
1. `langgraph` 依赖已声明但零使用，`langchain-openai` 仅作为 HTTP 客户端包装器（ChatOpenAI + 消息类转换）
2. 所有路由逻辑堆叠在单个 `routes.py`（430+ 行），意图分析和诊疗流程无复用
3. 私有辅助函数（`_build_intent_system_prompt`、`_build_clinic_system_prompt`）与路由耦合

**功能缺陷**：
1. `analyze_intent` 只做意图分类，history/suggest 意图无后处理（不拉取历史、不检索向量库、不生成回答）
2. `clinic_stream` 拉全量历史记录，无法按需筛选
3. go_ai_talk 的 history-service 不支持按事件ID筛选，Python 侧只能拉全量后过滤

**已有依赖**：`langgraph ^0.2.0`、`langchain-openai ^0.2.1` 已在 `pyproject.toml` 中声明。

## Goals / Non-Goals

**Goals:**

1. Go 侧新增 `/device/history/api/filter` API，支持多事件ID（逗号分隔）和时间范围筛选
2. 用 LangGraph StateGraph 编排意图分析流程（intent_graph），包含意图分类→路由→后处理完整链路
3. 用 LangGraph StateGraph 编排诊疗流程（clinic_graph），包含数据需求判断→按需拉取历史→向量检索→流式回答
4. 拆分路由文件：`routes/intent.py`、`routes/clinic.py`、`routes/health.py`
5. 抽取共享节点（一节点一文件），intent_graph 和 clinic_graph 复用
6. 提示词独立管理到 `graphs/nodes/prompts/` 目录
7. State 分离定义：IntentState 和 ClinicState 各自独立
8. 实现 history 意图后处理：判断数据需求→拉取历史→LLM 生成回答
9. 实现 suggest 意图后处理：判断数据需求→拉取历史+向量检索+宝宝画像→LLM 生成建议
10. clinic_graph 也走动态判断历史范围（复用 judge_data_requirement 节点）
11. 保持与 go_ai_talk 的兼容性（返回相同 JSON 结构、路由路径不变）
12. 所有新增代码添加中文业务逻辑注释

**Non-Goals:**

1. 不修改 `feeding` 和 `conversation` 意图的处理逻辑（保持简单返回）
2. 不修改 go_ai_talk 现有 API（`/device/history/api/list`、`/device/history/api/piece`）
3. 不涉及 CI/CD 流程调整
4. 不引入新的 LLM 提供商
5. 不修改 LLM 客户端的核心调用逻辑（保留 langchain-openai 的 ChatOpenAI 包装）

## Decisions

### D1: LangGraph StateGraph 编排替代手写 if/else

**决定**: 用 LangGraph 的 `StateGraph` 编排意图分析和诊疗流程，替代当前 `routes.py` 中的手写逻辑。

**理由**:
- 流程可视化：节点和条件边清晰表达意图分类后的分支逻辑
- 可复用：共享节点可被多个 graph 复用（如 `fetch_history`、`search_vectors`）
- 可观测：LangGraph 支持状态追踪，便于调试
- 符合设计初衷：项目已声明 `langgraph` 依赖，应当用起来

**替代方案**: 继续手写函数调用链 → 无法复用、调试困难、与设计文档不符

### D2: 两个独立 StateGraph（intent_graph + clinic_graph）

**决定**: 创建两个独立的 StateGraph，而非一个统一的大图。

**理由**:
- 两个接口的输入/输出差异大（intent 返回 JSON，clinic 返回 SSE 流）
- State 字段差异大，合并会增加理解成本
- 独立图更易维护和测试
- 通过共享节点实现代码复用

**替代方案**: 单一统一图 + 条件分支 → State 字段臃肿、条件逻辑复杂

### D3: State 分离定义（IntentState + ClinicState）

**决定**: 两个 graph 各自独立的 State 定义，不使用共享基类。

**理由**:
- IntentState 需要 `intent_result`、`data_requirement`、`event_dictionary` 等字段
- ClinicState 需要 `question`、`response_stream` 等字段
- 字段重叠度低（仅 `device_no`、`model_config`、`history_events` 共享），抽取基类收益不大
- 分离定义更直观，避免无关字段干扰

**替代方案**: BaseState 基类 + 子类继承 → 过度抽象、字段污染

### D4: 一节点一文件

**决定**: 每个 LangGraph 节点一个独立文件，存放在 `app/graphs/nodes/` 目录。

**理由**:
- 单一职责，每个文件专注一个功能
- 便于定位和修改
- 节点间无循环依赖
- 便于单独测试

**节点清单**:
| 文件 | 功能 | 被谁使用 |
|------|------|---------|
| `classify_intent.py` | 意图分类（LLM 调用） | intent_graph |
| `judge_data_requirement.py` | 判断需要哪些事件ID和时间范围（LLM 调用） | intent_graph + clinic_graph |
| `fetch_history.py` | 拉取历史记录（调用 filter API） | intent_graph + clinic_graph |
| `search_vectors.py` | 向量检索 | intent_graph(suggest) + clinic_graph |
| `fetch_baby_profile.py` | 获取宝宝画像 | intent_graph(suggest) + clinic_graph |
| `generate_response.py` | 同步生成回答（LLM 调用） | intent_graph |
| `stream_response.py` | 流式生成回答（LLM 流式调用） | clinic_graph |

**替代方案**: 按功能分组合并（data_nodes.py + llm_nodes.py） → 文件定位不直观、职责混淆

### D5: 提示词独立管理

**决定**: 将提示词构建函数从路由和节点中抽离，放到 `app/graphs/nodes/prompts/` 目录，每个节点对应的 prompt 一个文件。

**理由**:
- 提示词是迭代频率最高的部分，独立管理便于快速调整
- 与节点逻辑解耦，节点只负责调用 LLM 和处理结果
- 便于 A/B 测试不同提示词版本

**提示词清单**:
| 文件 | 用途 |
|------|------|
| `intent_classification.py` | 意图分类提示词 |
| `data_requirement.py` | 数据需求判断提示词 |
| `history_answer.py` | history 意图生成回答提示词 |
| `suggest_answer.py` | suggest 意图生成建议提示词 |
| `clinic_answer.py` | 诊疗场景生成回答提示词 |

### D6: Go 侧 Filter API 接收 eventIds（而非 eventNames）

**决定**: Go 侧新增的 `/device/history/api/filter` API 接收事件ID列表（逗号分隔），而非事件名称列表。

**理由**:
- 事件ID是稳定标识，事件名称会变化（业务运营可调整名称）
- 数据库查询按 ID 索引更高效
- LLM 判断数据需求时输出 event_ids，传入 API 无需额外转换

**API 设计**:
```
GET /device/history/api/filter
参数:
  deviceNo: string (必填)
  eventIds: string (可选) - 事件ID列表，逗号分隔，如 "1,2"
  startTime: int64 (可选) - 开始时间戳（毫秒）
  endTime: int64 (可选) - 结束时间戳（毫秒）
  limit: int (可选，默认 100)
```

### D7: clinic_graph 也走动态判断历史范围

**决定**: clinic_graph 在拉取历史前先调用 `judge_data_requirement` 节点，根据用户问题动态判断需要的事件类型和时间范围。

**理由**:
- 当前 clinic_stream 拉全量历史，数据量大且大部分无用
- 与 intent_graph 的 suggest 意图走同样的数据准备逻辑
- 减少数据传输量，提升响应速度

**代价**: 多一次 LLM 调用（判断数据需求），约增加 1-2 秒延迟。可通过与向量检索并行缓解。

### D8: 路由文件拆分策略

**决定**: 将 `app/api/routes.py` 拆分为 `app/api/routes/` 目录，每个接口一个文件。

**文件结构**:
```
app/api/routes/
├─ __init__.py         ← 汇总路由，创建 APIRouter
├─ intent.py           ← /v1/analyze/intent
├─ clinic.py           ← /v1/clinic/stream
└─ health.py           ← /v1/health
```

**理由**:
- 单一职责，每个文件只处理一个接口
- 便于独立测试和维护
- 路由路径不变，对外兼容

### D9: intent_graph 条件路由设计

**决定**: intent_graph 在 `classify_intent` 节点后使用条件边（conditional edge），根据 `target_type` 路由到不同分支。

**路由逻辑**:
```
classify_intent → 条件判断:
  - feeding → 直接返回（Go 侧处理 CRUD）
  - history → judge_data_requirement → fetch_history → generate_response
  - suggest → judge_data_requirement → fetch_history → search_vectors → fetch_baby_profile → generate_response
  - conversation → 兜底文案
  - exit → 直接返回
```

**实现方式**: 使用 `add_conditional_edges` 方法，根据 `state.intent_result.target_type` 决定下一节点。

## Risks / Trade-offs

### R1: LangGraph 学习曲线

**风险**: 团队不熟悉 LangGraph，增加理解和维护成本。

**缓解**:
- 每个节点是纯函数（输入 State，返回 State 更新），与普通函数无异
- 添加详细的中文业务逻辑注释
- 节点可独立测试，不依赖 LangGraph 运行时

### R2: 两阶段 LLM 调用增加延迟

**风险**: intent_graph 的 history/suggest 流程需要 2-3 次 LLM 调用（分类 + 判断数据需求 + 生成回答），延迟叠加。

**缓解**:
- feeding/conversation/exit 意图跳过阶段 2，直接返回
- judge_data_requirement 的 LLM 调用可设置较短超时和较低 max_tokens
- 后续可考虑将意图分类和数据需求判断合并为单次 LLM 调用

### R3: LLM 判断数据需求可能出错

**风险**: LLM 可能返回错误的事件ID或时间范围。

**缓解**:
- fallback 策略：LLM 返回异常时使用默认配置（事件ID为空=拉取所有，时间范围=最近7天）
- 事件字典校验：只接受在事件字典中存在的 event_ids
- 记录判断日志，便于监控和优化

### R4: Go 侧新 API 的版本依赖

**风险**: Python 服务依赖新 filter API，如果 Go 服务未升级到包含新 API 的版本，请求会失败。

**缓解**:
- Python 侧添加降级逻辑：filter API 不可用时回退到 `get_history_events` 拉取全量
- 部署文档明确版本依赖关系

### R5: 迁移期间的路由兼容性

**风险**: 拆分路由文件时可能引入路径或导入错误。

**缓解**:
- 路由路径不变（/v1/analyze/intent, /v1/clinic/stream, /v1/health）
- 逐步迁移：先创建新文件，再删除旧文件
- 迁移后运行健康检查验证

## Migration Plan

### 阶段 1: 目录结构搭建

1. 创建 `app/api/routes/` 目录，拆分路由文件
2. 创建 `app/graphs/` 目录结构（nodes/、prompts/、states/）
3. 删除旧 `app/api/routes.py`
4. 验证路由路径不变

### 阶段 2: Go 侧 Filter API

1. 新增 API 请求/响应模型定义
2. 在 HistoryCtrl 中新增 Filter 方法
3. 实现服务层过滤查询逻辑
4. 测试新 API

### 阶段 3: Python 侧共享节点

1. 实现 State 定义（IntentState, ClinicState）
2. 实现提示词文件（prompts/）
3. 实现共享节点（classify_intent, judge_data_requirement, fetch_history, search_vectors, fetch_baby_profile, generate_response, stream_response）
4. 在 http_client.py 中新增 `get_filtered_history_events` 方法
5. 逐个测试节点

### 阶段 4: LangGraph 编排

1. 实现 intent_graph（StateGraph + 条件边）
2. 实现 clinic_graph（StateGraph）
3. 在路由文件中调用 graph
4. 端到端测试

### 阶段 5: 清理与验证

1. 删除旧路由文件中的迁移代码
2. 更新文档
3. 全量回归测试

### 回滚策略

- Go 侧：新 API 不影响现有 API，无需回滚
- Python 侧：保留旧 `routes.py` 的备份，出现问题可快速切换
- LangGraph 节点可独立禁用，回退到手写逻辑
